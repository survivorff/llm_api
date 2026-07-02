"""加密货币充值适配器：USDT-TRC20（波场）。

设计（部署者友好、无需第三方支付牌照）：
- 下单时分配一个「收款地址 + 唯一金额」组合用于对账（金额尾数加随机小数区分订单）。
- 对账 worker 通过公开区块链 API（TronGrid）查询该地址的 TRC20 转账记录，
  匹配到金额一致且未处理的入账即视为支付成功。
- 无回调（supports_callback=False），完全靠轮询。

config:
  address:      收款 TRON 地址（TXXXX...）
  contract:     USDT 合约地址（默认主网 USDT-TRC20）
  api_url:      TronGrid 基址（默认 https://api.trongrid.io）
  api_key:      TronGrid API Key（可选，提升限额）
  usd_rate:     1 USDT = ? credits 的换算由订单服务处理，这里只认 amount_money（= 微 USDT，6 位精度）

注意：为避免同额并发歧义，订单服务给每个订单分配唯一的「金额尾数」。
"""
from __future__ import annotations

import time

import httpx

from .base import PaymentProvider, PaymentRequest, PaymentResult

DEFAULT_CONTRACT = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"  # USDT-TRC20 主网合约


class CryptoProvider(PaymentProvider):
    name = "crypto"
    supports_callback = False  # 靠对账 worker 轮询链上

    async def create_payment(self, req: PaymentRequest) -> PaymentResult:
        address = self.config.get("address")
        if not address:
            return PaymentResult(ok=False, error="crypto wallet address not configured")
        # amount_money 单位：微 USDT（6 位精度）。展示为 USDT 金额。
        usdt = req.amount_money / 1_000_000
        return PaymentResult(
            ok=True,
            pay_address=address,
            pay_url=f"tron:{address}?amount={usdt:.6f}",
            extra={"amount_usdt": f"{usdt:.6f}", "contract": self.config.get("contract", DEFAULT_CONTRACT),
                   "network": "TRC20"},
        )

    async def query_status(self, order_no: str, provider_order: str | None) -> bool:
        """查询收款地址最近的 TRC20 入账，匹配订单唯一金额。

        provider_order 里存放期望的精确金额（微 USDT，字符串）。
        """
        address = self.config.get("address")
        if not address or not provider_order:
            return False
        api_url = self.config.get("api_url", "https://api.trongrid.io").rstrip("/")
        contract = self.config.get("contract", DEFAULT_CONTRACT)
        headers = {}
        if self.config.get("api_key"):
            headers["TRON-PRO-API-KEY"] = self.config["api_key"]

        url = f"{api_url}/v1/accounts/{address}/transactions/trc20"
        params = {"limit": 50, "contract_address": contract, "only_confirmed": "true"}
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.get(url, params=params, headers=headers)
                data = resp.json()
        except Exception:
            return False

        try:
            expected = int(provider_order)
        except (TypeError, ValueError):
            return False

        now_ms = time.time() * 1000
        for tx in data.get("data") or []:
            # 只认最近 2 小时内、转入本地址、金额精确匹配的交易
            if tx.get("to") != address:
                continue
            ts = tx.get("block_timestamp", 0)
            if now_ms - ts > 2 * 3600 * 1000:
                continue
            try:
                value = int(tx.get("value", "0"))  # USDT 6 位精度的整数
            except (TypeError, ValueError):
                continue
            if value == expected:
                return True
        return False

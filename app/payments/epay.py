"""易支付（EPay）聚合适配器：覆盖微信 / 支付宝扫码。

易支付是国内常见的聚合支付协议（彩虹易支付等兼容实现）。
协议要点：
- 下单：GET/POST 提交 pid + 参数 + MD5 签名，返回支付二维码/跳转
- 回调：GET/POST notify_url，带 sign，需按同样规则验签
- 签名：参数按 key 升序拼接 + 商户密钥，MD5

config:
  api_url:   易支付网关地址（如 https://pay.example.com）
  pid:       商户 ID
  key:       商户密钥
  notify_url / return_url: 回调与跳转地址
"""
from __future__ import annotations

import hashlib
from urllib.parse import urlencode

import httpx

from .base import CallbackResult, PaymentProvider, PaymentRequest, PaymentResult


def _md5_sign(params: dict, key: str) -> str:
    """易支付签名：过滤空值/sign/sign_type，按 key 升序拼接，尾接商户密钥后 MD5。"""
    items = sorted(
        (k, v) for k, v in params.items()
        if v not in ("", None) and k not in ("sign", "sign_type")
    )
    raw = "&".join(f"{k}={v}" for k, v in items) + key
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


class EPayProvider(PaymentProvider):
    name = "epay"
    supports_callback = True

    async def create_payment(self, req: PaymentRequest) -> PaymentResult:
        api_url = self.config.get("api_url", "").rstrip("/")
        pid = self.config.get("pid")
        key = self.config.get("key")
        if not (api_url and pid and key):
            return PaymentResult(ok=False, error="epay not configured")

        # 支付方式：extra.channel 指定 alipay/wxpay，默认 alipay
        pay_type = req.extra.get("channel", "alipay")
        params = {
            "pid": pid,
            "type": pay_type,
            "out_trade_no": req.order_no,
            "notify_url": self.config.get("notify_url", ""),
            "return_url": self.config.get("return_url", ""),
            "name": req.subject,
            # 易支付金额单位是「元」，两位小数
            "money": f"{req.amount_money / 100:.2f}",
        }
        params["sign"] = _md5_sign(params, key)
        params["sign_type"] = "MD5"

        # 使用 mapi.php（API 下单）优先，返回 JSON（含二维码/跳转）
        mapi = f"{api_url}/mapi.php"
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(mapi, data=params)
                data = resp.json()
        except Exception as e:
            # 回退：直接构造 submit.php 跳转链接（页面下单）
            submit = f"{api_url}/submit.php?" + urlencode(params)
            return PaymentResult(ok=True, pay_url=submit, extra={"mode": "redirect", "warn": str(e)})

        if str(data.get("code")) != "1":
            return PaymentResult(ok=False, error=data.get("msg") or "epay create failed")
        return PaymentResult(
            ok=True,
            pay_url=data.get("payurl") or data.get("qrcode") or data.get("urlscheme"),
            provider_order=data.get("trade_no"),
            extra={"mode": "qrcode" if data.get("qrcode") else "redirect"},
        )

    def verify_callback(self, headers: dict, body: bytes, form: dict) -> CallbackResult:
        key = self.config.get("key")
        if not key or not form:
            return CallbackResult(ok=False)
        sign = form.get("sign")
        expect = _md5_sign(form, key)
        if not sign or sign != expect:
            return CallbackResult(ok=False, raw=dict(form))
        paid = form.get("trade_status") in ("TRADE_SUCCESS", "SUCCESS") or form.get("trade_status") is None
        money = None
        try:
            money = int(round(float(form.get("money", 0)) * 100))
        except Exception:
            pass
        return CallbackResult(
            ok=bool(paid),
            order_no=form.get("out_trade_no"),
            provider_order=form.get("trade_no"),
            amount_money=money,
            raw=dict(form),
        )

    async def query_status(self, order_no: str, provider_order: str | None) -> bool:
        api_url = self.config.get("api_url", "").rstrip("/")
        pid = self.config.get("pid")
        key = self.config.get("key")
        if not (api_url and pid and key):
            return False
        params = {"act": "order", "pid": pid, "out_trade_no": order_no}
        params["sign"] = _md5_sign(params, key)
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(f"{api_url}/api.php", params=params)
                data = resp.json()
            return str(data.get("status")) == "1"
        except Exception:
            return False

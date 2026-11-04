# -*- coding=UTF-8 -*-
# @Project          QL_TimingScript
# @fileName         中国移动云盘.py
# @author           Echo
# @EditTime         2026/10/15
# cron: 0 0 8,10,12,15 * * *   （每 4 小时一轮：云盘日/限量活动都在整点开）
# const $ = new Env('中国移动云盘');
"""
中国移动云盘（云朵中心 / 云盘专属 AI豆）签到脚本

─────────────────────────── 环境变量 ───────────────────────────
  ydyp_ck           必需   账号凭据，多账号用 @ 分隔
  ydyp_ua           必需   自己手机的 User-Agent（抓包复制完整整串）；不填直接退出
  ydyp_device_id    可选   全局默认设备号（UUID）；ydyp_ck 第 4 段可单独覆盖它
  ydyp_device_token 强烈建议 真机设备令牌（约 88 字符 base64）；不填则签到/领记录豆会回 614
  AI 相机需同目录 assets/ai_camera_sample.jpg；缺失时提示并跳过，其他任务继续。

  ydyp_ck 格式（# 分隔，后两段可省）：
      <authorization>#<手机号>#<jwtToken>#<deviceId>
  例：ydyp_ck=Basic bW9iaWxl....xxx#13800000000
  多账号：ydyp_ck=账号1@账号2@账号3
  正常运行时，登录前用 Basic authorization + 手机号调用 /user/auth/refreshToken。
  刷新成功后只替换手机号匹配账号的 Authorization，保留其他账号及可选字段；
  青龙运行时更新面板中的 ydyp_ck，Windows 本地运行时更新当前用户环境变量。
  持久化失败不影响本轮使用，但下轮仍会读到旧值；--check 保持只读，不调用刷新接口。

──────────────────── 这些值怎么拿到（手机抓一次包就够）────────────────────
  抓包工具：手机装 Reqable（推荐）或 Stream；也可用本仓库附带的 PC 抓取工具
            「移动云盘抓authorization.zip」（解压后右键管理员运行，自动抓出 authorization）。

  authorization   抓「中国移动云盘」App 的任意一条请求，看请求头里的 authorization
                  （形如 Basic bW9iaWxl...，是一整串）；云朵中心 H5（浏览器打开
                  m.mcloud.139.com/portal/newsignin/ 并登录）的请求头里也有同一个值。
                  刷新接口若拒绝旧凭据，且登录仍返回「05050006 暂无权限！」，
                  需要重新抓包替换 ydyp_ck；自动刷新不能保证恢复已失效的凭据。
  手机号          登录用的移动手机号；用于脱敏展示、派生设备号，以及加密提交至官方刷新接口。
  jwtToken        （可省）抓 tyrzLogin 响应里的 result.token（形如 eyJhbGci....xx.yy）。
                  填了会先用它、失效自动回退到 authorization 重换；不填每轮现换也行。
  deviceId        （可省）抓 tyrzLogin 请求体里的 deviceId（UUID 形式）。
                  不填则由脚本按账号派生：每个账号稳定、各人互不相同，无需手填。
  ydyp_device_token （强烈建议）抓任意一条 App 领取请求，复制请求体里的 deviceId 整串
                  （形如 AbCdEf012345...Q==，约 88 字符 base64）。抓法：抓包工具里搜
                  receiveV3（或搜你待领记录的那串数字 ID），看这条 POST 的请求体：
                    {"client":"app","cloudId":...,"cloudType":0,"deviceId":"<就是这一串>"}
                  它由 App 内置 SMSdk 依设备指纹生成、本机固定，抓一次可长期用。
  ydyp_ua         （必需）抓包里复制任意请求的完整 User-Agent 整串（含结尾的 MCloudApp/版本）。
                  必须各填各的：它要和自己的设备令牌配套，UA 与设备对不上本身就是风险信号，
                  多人共用一串也等于「同一台设备」。不填脚本直接退出。

──────────────────────────── 风控建议 ────────────────────────────
  · 一账号一设备指纹：ydyp_ua + 设备令牌各填各的；deviceId 默认值已按账号派生，各人天然不同。
  · 不要把 ck 借给别人用（同一 ck 多 IP 登录本身就会触发风控）；也不要多机同跑一个账号。

覆盖的领豆入口（均以 App/H5 接口面为准）：
  A. 云朵中心 sign_in_3
     1) 每日签到 startSignIn
     2) 签到翻倍 multiple（每月一次）
     3) 任务点击 task/click + 逐条领奖 receiveTask（含 FINISH 已完成的补领）
     4) 记录豆领取 receiveV3（含 cloudType=1 的膨胀/月度奖励 receiveTaskExpansion）
     5) 106 保留 OSE 上传并增加个人云回退；522 使用个人云批量补足并回查进度
  B. 老 market 接口（实测存活）：连续备份奖励 backupgift（读接口已切新域）、通知任务 msgPushOn
  C. 独立活动巡检 activity_patrol：直播间小红花、年度回馈开福袋、TokenPK 阶段奖励、云盘日盲盒/礼品、邮箱短信
     —— 每个活动先查状态，只在「可领/有库存/有次数」时才动作，无库存/已领/已结束自动跳过。
  D. 从 mcloud.py 合入：V2 分组任务补全、分享434、AI相机585、回忆上传587、问AI588、
     九宫格模板589、多步骤 task2、戳一戳15次、139邮箱任务、老抽奖尝试（每轮最多1次）。
     新增个人云临时文件只按本轮创建 ID 移入回收站，不扫描清理历史文件。

说明：
  1) 凭据三种形态脚本都认：Basic authorization（推荐）/ ssoToken / 裸 jwtToken（eyJhbGci....xx.yy）。
     直填 jwtToken 时脚本先探活再使用，失效会自动回退到 authorization 重换，不会一路空跑。
  2) 设备标识有两套，别混淆：
     a) 明文设备号（UUID）：走头部 deviceId / 登录请求体。优先级：ydyp_ck 第 4 段 >
        ydyp_device_id > 按账号派生（一个账号固定一个、各人互不相同）。一般不用手填。
     b) 加密设备令牌：签到 startSignIn（URL 参数）、领记录豆 receiveV3（请求体）、兑换
        exchangeV3 这几个接口会带上它，服务端据此确认「设备已登记」。不填一律回
        614「活动太火爆啦，锁定失败」——实测同账号同请求，仅补上这串即领取成功。
        抓法见上方 ydyp_device_token。
  3) 依赖：httpx、python-dotenv；Authorization 刷新和九宫格账号加密另需 pycryptodome。
     同目录需 log.py / get_env.py / sendNotify.py（原项目自带，需一起下载）。
     pip 装依赖：pip install httpx python-dotenv pycryptodome
  4) 兑换接口带滑块验证（getSlidePuzzle + puzzleOffset），脚本无法完成。
  5) 522 已切换为 mcloud.py 的个人云 file/create 协议，自动按缺口补足，最多三轮；
     每轮回查任务进度，不增长即停止。该协议只登记文件，不发送文件内容，
     是否计入任务取决于服务端；不计数时仍需真实上传/PC 客户端累计。
     587 同样沿用源脚本的 JPG 文件登记方式；589 仅获取模板并登记任务，不实际生成图片。
  6) 老抽奖 playoffic 已加入有额度时的单次尝试，602 表示活动结束，残留额度不代表可中奖。
     · 微信公众号签到 followSignInfo：602 活动已结束。
     · 中秋灯谜（窗口 2026-10-07 截止）、酷狗联合活动（602 已结束）本就未接入。
  7) 云盘日（会员日）每月 16 号 10:00 开窗，10/12/15 点各放一波限量礼品（库存看 totalCount/hasStock）：
     · 未开窗时 /mcloudday/gift/* 与 blindbox/* 整体 404（活动按窗口上下线）→ 先查 online 再动作，
       未开窗只打一行提示，不再逐条试探 20+ 礼品刷屏（2026-10-15 旧版刷满一屏 404 就是这么来的）。
     · **动作接口比读接口多两道门槛**：① 必须带 JSON body（抽奖体 {"client":"1"}，App 端取值）
       ② 必须带 isDeviceId 设备头；缺任一项网关直接回 nginx 404（不是业务码）。2026-10-16 实测对照：
       POST {} → 404；POST {"client":"1"} + 设备头 → 200 code:0 且 lotteryCount 同步 -1。
     · 惊喜助力礼按邀请人数分档（inviteCount 1/4/10），未达门槛回 40001「未满足惊喜奖品条件」。
     · 礼品领取**必须带 smsCode 字段**（值可空码 MD5("")）：实测只发 {prizeId} 会回 nginx 404；
       需短信验证码的奖品回 10004「验证码错误」，脚本按 msg 提示到 App 内手领。
  8) 老 market 域 caiyun.feixin.10086.cn 会间歇性 DNS 解析失败（[Errno -3] Try again：实测同一轮
     5 个请求里 3 个失败、2 个成功，同日重试即恢复）。脚本对「请求未发出」的连接类错误自动重试
     3 次（1s/2s 退避），读取接口失败再回退一次；读超时不重试，避免抽奖类接口被重复提交。
  9) 本轮核对过、但**没有加入**的现役活动（附原因，省得下次重复调研）：
     · 13 周年升级礼 National_v13gift（2026-04-27~12-31）：领奖要短信验证码（getPrize?smsCode=）。
     · 玩 AI National_playAI（~2026-12-31）：抽奖次数靠完成 H5 里的 AI 玩法任务（抠图/漫画/转录），
       纯接口做不了。
     · 使用时长反馈 National_sessionDuration（2026-09-30~10-31）：acceptPrize 需短信验证码。
     · 红骑兵 2026 National_RedCavalry2026（~12-31）：打卡/答题接口可用，但活动本身不发 AI豆（只有勋章）。
     · TokenPK 任务 /ycloud/tokenpk/task/list：该路由未部署（404），只能用阶段奖励（脚本已覆盖）。
     · 集卡/美图抽奖/备图/酷狗/转赠红包等：接口 404 或活动窗口已结束。
  10) **任务奖励是服务端「异步记账」的**（issue #50 根因）：任务 state 变 FINISH 是即时的，但奖励要过一会儿
     才以「记录豆」（infoV3.receiveList）形式出现。同一账号实测：08:00 传完文件当次 receiveTask 全 0、
     记录豆为空（结束只 +3 = 签到），10:00 再跑才看到「待领 6」并在记录豆通道领到 +6 ——
     用户感知就是「每天第一遍领不到、要跑两遍」。脚本因此在任务段结束后刷新状态并有限轮询补领
     （settle_task_rewards，总预算见 WAIT_SETTLE）；记账超出预算也不影响正确性，下一轮定时任务会补领。
"""
import asyncio
import base64
import hashlib
import json
import os
import random
import re
import sys
import time
import uuid
from datetime import datetime, timezone, timedelta

import httpx

import log
from get_env import get_env
from sendNotify import send_notification_message_collection

try:
    from dotenv import load_dotenv, find_dotenv
    
    load_dotenv(find_dotenv())
except Exception:
    pass

UA = (os.environ.get("ydyp_ua") or "").strip()  # 必需：自己手机的完整 User-Agent（抓包可得，与设备令牌配套）
DEVICE_ID_ENV = (os.environ.get("ydyp_device_id") or "").strip()  # 全局默认设备号（被 ydyp_ck 第 4 段覆盖）
DEVICE_TOKEN = (os.environ.get("ydyp_device_token") or "").strip()

H5 = "https://m.mcloud.139.com"  # 新接口平台（与云朵中心 H5 同源）
YCLOUD = H5 + "/ycloud"
MARKET = "https://caiyun.feixin.10086.cn"  # 老 market 平台（抽奖/备份/通知仍在此）
SIGN_SALT = "sekaMdYYLIZfbCfm"  # x-signature 盐值（前端 char-code 混淆还原）
SOURCE_ID = "001005"  # 云盘渠道号：换 ssoToken 与登录必须一致
CLIENT_VERSION = "13.2.2"
APP_VERSION = CLIENT_VERSION + ".0"  # 头部 appVersion（真机同款，跟随上一行）
MARKET_NAME = "sign_in_3"
GIFT_SMS_CODE = "d41d8cd98f00b204e9800998ecf8427e"  # MD5("")：云盘日领取的 smsCode 字段必须存在（值可空码，需短信的奖品会回 10004 验证码错误）  # 云朵中心活动标识
UPLOAD_MARKET = "National_redCavalry"  # OSE 上传通道唯一可用活动（实测 8 个候选仅此通过）
# 任务奖励异步记账的补领轮询间隔（秒，累加约 165s）：只在本轮执行过任务时等待。
WAIT_SETTLE = (10, 20, 30, 45, 60)  # ≈165s 总预算
SIGN_SETTLE = (2, 3, 5, 8)  # 签到结果回查节流（≈18s）
AI_TOOL_ACCOUNT_AES_KEY = "xuL97!x7GGxG%8V4"
AI_TOOL_ACCOUNT_AES_IV = "5OuCxk4XNu0NA*%x"


def _md5(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def _sign_headers(params_str: str = "") -> dict:
    """云朵中心网关签名头：x-signature = MD5(salt + rid + ts + nonce + params串 + salt)"""
    rid, nonce = str(uuid.uuid4()), str(uuid.uuid4())
    ts = str(int(time.time() * 1000))
    return {"x-request-id": rid, "x-timestamp": ts, "x-nonce": nonce,
            "x-signature": _md5(SIGN_SALT + rid + ts + nonce + params_str + SIGN_SALT)}


def _require_ua() -> bool:
    """UA 是必需项：必须填自己手机的 UA（与设备令牌配套），缺失直接退出。"""
    if UA:
        return True
    log.log("❌ 未配置环境变量 ydyp_ua（必需项）—— 抓包复制任意请求的完整 User-Agent 整串填进来")
    log.log("   形如：Mozilla/5.0 (Linux; Android 15; <你的机型> Build/XXX; wv) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Version/4.0 Chrome/XXX Mobile Safari/537.36 MCloudApp/<版本>")
    return False

def _replace_account_authorization(value: str, account: str, authorization: str):
    entries = value.split("@") if value else []
    found = False
    for index, entry in enumerate(entries):
        fields = entry.split("#")
        if len(fields) > 1 and fields[1].strip() == account:
            fields[0] = authorization
            entries[index] = "#".join(fields)
            found = True
    return "@".join(entries) if found else None


def _load_qinglong_token():
    auth_files = [item for item in (os.getenv("QL_AUTH_FILE"), "/ql/data/db/keyv.sqlite",
                                     "/ql/data/config/auth.json", "/ql/config/auth.json") if item]
    auth_files.sort(key=lambda item: os.path.getmtime(item) if os.path.exists(item) else -1, reverse=True)
    for auth_file in auth_files:
        try:
            if auth_file.endswith(".sqlite"):
                with open(auth_file, "rb") as file:
                    matches = re.findall(rb'"token"\s*:\s*"([^"]+)"', file.read())
                token = matches[-1].decode("utf-8") if matches else ""
            else:
                with open(auth_file, "r", encoding="utf-8") as file:
                    data = json.load(file)
                token = data.get("token") if isinstance(data, dict) else ""
            if token:
                return token
        except (OSError, UnicodeError, ValueError, TypeError):
            continue
    return None


class MobileCloudDisk:
    """中国移动云盘 —— 云朵中心（AI豆）任务执行器"""
    
    def __init__(self, cookie: str):
        fields = (cookie or "").split("#")
        self.authorization = fields[0].strip() if fields else ""
        self.account = fields[1].strip() if len(fields) > 1 else ""
        self.token = fields[2].strip() if len(fields) > 2 else ""
        # 设备号优先级：ydyp_ck 第 4 段 > ydyp_device_id > 按账号派生（UUID 形式，稳定且各账号互不相同）
        self.device_id = (fields[3].strip() if len(fields) > 3 and fields[3].strip()
                          else DEVICE_ID_ENV
                               or str(uuid.uuid5(uuid.NAMESPACE_DNS, "ydyp:" + (self.account or "unknown"))))
        self.show_account = ((self.account[:3] + "****" + self.account[-4:])
                             if len(self.account) >= 11 else self.account)
        self.jwt = ""
        self.beans = None
        self.signed_today = None
        self.info = {}  # infoV3 全量结果（含 receiveList）
        self.user_domain_id = ""
        self.created_files = []
        self.client = httpx.AsyncClient(verify=False, timeout=60, follow_redirects=True)
        self.base_headers = {"User-Agent": UA, "Accept": "*/*",
                             "Referer": H5 + "/portal/newsignin/index.html", "Origin": H5,
                             "deviceId": self.device_id}
    
    # ── 基础设施 ────────────────────────────────────────────────────────
    def _h(self, extra: dict = None) -> dict:
        h = dict(self.base_headers)
        if self.jwt:
            h["jwtToken"] = self.jwt
        if extra:
            h.update(extra)
        return h
    
    def _dev_h(self, extra: dict = None) -> dict:
        """真机同款设备头：isDeviceId 让网关校验「体/参数里的 deviceId」。
        未配 ydyp_device_token 时保持原样"""
        h = self._h(extra)
        if DEVICE_TOKEN:
            h.pop("deviceId", None)  # App 不在头部带设备号，设备号走请求体 / URL 参数
            h.update({"isDeviceId": "true", "activityId": MARKET_NAME,
                      "appVersion": APP_VERSION, "x-requested-with": "com.chinamobile.mcloud"})
        return h
    
    async def _req(self, method: str, url: str, **kw):
        """统一请求 + JSON 解析；异常吞掉返回 None，避免单点失败中断整轮。
        连接/DNS 类失败自动重试 3 次（1s/2s 退避）：运维实测老 market 域
        caiyun.feixin.10086.cn 会间歇性解析失败（[Errno -3] Try again），单次失败不等于接口下线。
        注意只重试「请求没发出去」的错误（ConnectError/ConnectTimeout/DNS），
        读超时（ReadTimeout）不重试，避免抽奖这类会消耗次数的接口被重复提交。
        quiet=True 时不再打印「非 JSON 响应」告警——给预期可能 404/未部署的探测型接口用。"""
        quiet = kw.pop("quiet", False)
        tries = int(kw.pop("tries", 3))
        for attempt in range(1, tries + 1):
            try:
                resp = await self.client.request(method, url, **kw)
            except (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout,
                    httpx.ProxyError, OSError) as e:
                if attempt < tries:
                    await asyncio.sleep(1.0 * attempt)  # 给 DNS/连接一点恢复时间
                    continue
                if not quiet:
                    log.log(f"    ❌ 请求失败（已重试 {tries} 次）{url.split('?')[0]}: {e}")
                return None
            except Exception as e:
                log.log(f"    ❌ 请求异常 {url.split('?')[0]}: {e}")
                return None
            try:
                return resp.json()
            except ValueError:
                if not quiet:
                    snippet = " ".join(resp.text.split())[:100]  # 404 会回整页 HTML，压成单行再入日志
                    log.log(f"    ⚠️ 非 JSON 响应 {resp.status_code}: {snippet}")
                return None
        return None
    
    async def _yget(self, path: str, params: dict = None, quiet: bool = False, dev: bool = False):
        """dev=True：按真机方式把设备令牌放进 URL 参数（startSignIn 就是这样）。"""
        params = dict(params or {})
        if dev and DEVICE_TOKEN:
            params["deviceId"] = DEVICE_TOKEN
        return await self._req("GET", YCLOUD + path, params=params,
                               headers=self._dev_h() if dev else self._h(), quiet=quiet)
    
    async def _ypost(self, path: str, payload: dict = None, quiet: bool = False, dev: bool = False):
        """dev=True：按真机方式把设备令牌放进请求体（receiveV3 就是这样）。"""
        jh = {"Content-Type": "application/json;charset=UTF-8"}
        payload = dict(payload or {})
        if dev and DEVICE_TOKEN:
            payload["deviceId"] = DEVICE_TOKEN
        return await self._req("POST", YCLOUD + path, json=payload,
                               headers=(self._dev_h(jh) if dev else self._h(jh)), quiet=quiet)
    
    async def _mget(self, path: str):
        """老 market 接口（抽奖 / 备份 / 通知）"""
        return await self._req("GET", MARKET + path, headers=self._h())
    
    async def _balance(self):
        """读豆余额（infoV3.result.total 为权威值）"""
        r = await self._yget("/signin/page/infoV3", {"client": "app"})
        if r and r.get("code") == 0:
            self.info = r.get("result") or {}
            return self.info.get("total")
        r = await self._yget("/signin/page/getCloudNum", {"client": "app"})
        return (r or {}).get("result") if r and r.get("code") == 0 else None
    
    async def _jwt_alive(self) -> bool:
        """探一下当前 jwtToken 是否仍然可用（只读接口，无副作用）"""
        r = await self._yget("/signin/page/infoV3", {"client": "app"})
        return bool(r and r.get("code") == 0 and r.get("result"))
    
    async def _persist_authorization(self):
        current = os.environ.get("ydyp_ck", "")
        updated = _replace_account_authorization(current, self.account, self.authorization)
        if updated is None:
            log.log("  ⚠️ Authorization 已刷新，但 ydyp_ck 中未找到对应手机号，未持久化")
            return False
        os.environ["ydyp_ck"] = updated

        if os.name == "nt":
            try:
                import winreg
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
                    winreg.SetValueEx(key, "ydyp_ck", 0, winreg.REG_SZ, updated)
                log.log("  ✅ 已更新 Windows 当前用户环境变量 ydyp_ck")
                return True
            except OSError as error:
                log.log(f"  ⚠️ Windows 环境变量更新失败，本轮仍使用刷新值：{error}")
                return False

        token = _load_qinglong_token()
        if not token:
            log.log("  ⚠️ 未找到青龙授权信息，ydyp_ck 仅在本轮进程中更新")
            return False
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json;charset=UTF-8"}
        url = "http://127.0.0.1:5600/api/envs"
        result = await self._req("GET", url, params={"searchValue": "ydyp_ck", "t": int(time.time() * 1000)},
                                 headers=headers, tries=1, quiet=True)
        matches = [item for item in ((result or {}).get("data") or [])
                   if isinstance(item, dict) and item.get("name") == "ydyp_ck"]
        if len(matches) != 1:
            log.log(f"  ⚠️ 青龙中 ydyp_ck 匹配到 {len(matches)} 条，拒绝不明确的更新")
            return False
        env = matches[0]
        env_id = env.get("id") or env.get("_id")
        if not env_id:
            log.log("  ⚠️ 青龙 ydyp_ck 缺少环境变量 ID，未持久化")
            return False
        payload = {"name": "ydyp_ck", "value": updated,
                   ("id" if env.get("id") else "_id"): env_id}
        if env.get("remarks") is not None:
            payload["remarks"] = env["remarks"]
        result = await self._req("PUT", url, json=payload, headers=headers, tries=1, quiet=True)
        if (result or {}).get("code") not in (0, 200):
            log.log("  ⚠️ 青龙 ydyp_ck 更新失败，本轮仍使用刷新值")
            return False
        log.log("  ✅ 已更新青龙环境变量 ydyp_ck")
        return True

    async def _refresh_authorization(self):
        """沿用 mcloud.py 的小程序刷新协议；失败时保留原凭据继续登录。"""
        if not self.authorization.lower().startswith("basic "):
            return
        if not self.account:
            log.log("  Authorization 刷新已跳过：缺少手机号")
            return
        try:
            from Crypto.Cipher import AES
            from Crypto.Util.Padding import pad
        except ImportError:
            log.log("  未安装 pycryptodome，跳过 Authorization 刷新，继续使用原凭据")
            return

        payload = json.dumps({"phoneNumber": self.account}, separators=(",", ":")).encode("utf-8")
        cipher = AES.new(b"c7lXOigXahPnTViq", AES.MODE_ECB)
        encrypted = base64.b64encode(cipher.encrypt(pad(payload, AES.block_size))).decode("ascii")
        headers = {
            "Content-Type": "application/json",
            "User-Agent": ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) "
                           "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 "
                           "MicroMessenger/8.0.47(0x18002f2c) NetType/WIFI Language/zh_CN "
                           "miniProgram/wx4e4ed37286c816c2"),
            "x-yun-tid": str(uuid.uuid4()),
            "Authorization": self.authorization,
            "x-yun-api-version": "v1",
            "x-yun-module-type": "100",
            "x-yun-op-type": "1",
            "x-yun-app-channel": "10214200",
            "x-yun-client-info": "||8||||||||||||",
            "hcy-cool-flag": "1",
        }
        r = await self._req("POST", "https://user-njs.yun.139.com/user/auth/refreshToken",
                            headers=headers, json={"data": encrypted}, tries=1, quiet=True)
        if not isinstance(r, dict):
            log.log("  Authorization 刷新失败：接口无有效响应，继续使用原凭据")
            return
        code = str(r.get("code", ""))
        data = r.get("data")
        if not (r.get("success") is True or code in ("0", "00", "000", "0000")) or not isinstance(data, dict):
            log.log(f"  Authorization 刷新失败（code={code or 'unknown'}），继续使用原凭据")
            return
        raw_token = data.get("token")
        if not isinstance(raw_token, str) or not raw_token.strip():
            log.log("  Authorization 刷新失败：响应缺少有效 token，继续使用原凭据")
            return
        self.authorization = "Basic " + base64.b64encode(
            f"mobile:{self.account}:{raw_token}".encode("utf-8")).decode("ascii")
        log.log("  Authorization 自动刷新成功")
        await self._persist_authorization()

    async def login(self) -> bool:
        if self.jwt:
            return True
        # 形态 1/2：第 1 段或第 3 段直接是 jwtToken
        for cand, label in ((self.authorization, "第1段"), (self.token, "第3段")):
            if cand.count(".") == 2 and len(cand) > 80:
                self.jwt = cand
                if await self._jwt_alive():
                    log.log(f"  🔑 使用{label}直填的 jwtToken（{self.show_account}）")
                    return True
                self.jwt = ""
                log.log(f"  ⚠️ {label}填的 jwtToken 已失效")
                if label == "第1段":  # 第 1 段是 jwt 时没有可回退的凭据
                    log.log("  ❌ 请重新抓包替换 ydyp_ck（第 1 段应填 Basic authorization）")
                    return False
        
        sso = await self._query_sso_token()
        if sso and await self._tyrz_login(sso):
            return True
        return False
    
    async def _query_sso_token(self):
        """① authorization → ssoToken（toSourceId 必须与登录 sourceId 一致，实测 001005）"""
        r = await self._req("POST", "https://user-njs.yun.139.com/user/querySpecTokenV2",
                            headers={"authorization": self.authorization, "User-Agent": UA,
                                     "Content-Type": "application/json"},
                            json={"toSourceId": SOURCE_ID})
        if r and r.get("success") and (r.get("data") or {}).get("token"):
            return r["data"]["token"]
        if (r or {}).get("code") == "05050006":
            log.log("  ❌ authorization 已失效（05050006 暂无权限），请重新抓包更新 ydyp_ck")
        else:
            log.log(f"  ❌ 换取 ssoToken 失败：{r}")
        return None
    
    async def _tyrz_login(self, sso: str) -> bool:
        """② ssoToken → jwtToken（POST JSON；签名字符串为空串）"""
        body = {"token": sso, "openAccount": False,
                "marketName": MARKET_NAME, "sourceId": SOURCE_ID}
        h = {"Content-Type": "application/json;charset=UTF-8", "type": "signupPlatform",
             "deviceId": self.device_id, "User-Agent": UA,
             "Referer": H5 + "/portal/newsignin/index.html", "Origin": H5}
        h.update(_sign_headers(""))
        r = await self._req("POST", H5 + "/ycloud/auth-service/auth/tyrzLogin",
                            content=json.dumps(body, separators=(",", ":")), headers=h)
        if r and r.get("code") == 0 and (r.get("result") or {}).get("token"):
            self.jwt = r["result"]["token"]
            log.log(f"  🔑 登录成功（{self.show_account}）")
            return True
        log.log(f"  ❌ 换取 jwtToken 失败：{r}")
        return False
    
    async def query_status(self, quiet=False):
        """签到状态（infoV3）+ 豆余额 + 待领明细。quiet=True 只刷新 self.info 不打日志（供补领轮询用）"""
        r = await self._yget("/signin/page/infoV3", {"client": "app"})
        if r and r.get("code") == 0:
            res = r.get("result") or {}
            self.info = res
            today = datetime.now().day
            item = next((x for x in (res.get("cal") or [])
                         if x.get("d") == today and x.get("currentMonth") == 1), None)
            self.signed_today = bool(item and item.get("s"))
            self.beans = res.get("total")
            if not quiet:
                log.log("  📅 签到：%s（连签 %s 天｜本月 %s 天｜单次 +%s 豆）"
                        % ("今日已签 ⏭️" if self.signed_today else "今日未签 🉑",
                           res.get("signCount"), res.get("monthDays"), res.get("signInPoints")))
                log.log(f"  🫘 AI豆余额：{self.beans}（接口标记待领 {res.get('toReceive')}）")
            return res
        log.log(f"  ⚠️ 查询签到状态失败：{r}")
        return None
    
    async def sign_in(self):
        """点击即签到（接口幂等：今日已签仍返回 todaySignIn=true）"""
        r = await self._yget("/signin/page/startSignIn", {"client": "app"}, dev=True)
        if r and r.get("code") == 0:
            res = r.get("result") or {}
            # startSignIn 的响应读的是从库，三种情况都实测到过：
            #   ① todaySignIn=True             → 成功
            #   ② todaySignIn=False 但日历已签  → 成功（issue #50 用户日志）
            #   ③ todaySignIn=False 且日历未签  → 也可能成功（全新账号实测：当场都显示未签，
            #      事后余额 +3、日历变已签）
            # → 当场判不了，回查 infoV3 复核几次再下结论，避免误报「签到未生效」
            today = datetime.now().day

            def _signed_of(x):
                cell = next((c for c in (x.get("cal") or [])
                             if c.get("d") == today and c.get("currentMonth") == 1), None)
                return bool(x.get("todaySignIn")) or bool(cell and cell.get("s"))

            ok, sig, waited = _signed_of(res), "接口返回", 0
            if not ok:
                for w in SIGN_SETTLE:
                    await asyncio.sleep(w)
                    waited += w
                    r2 = await self._yget("/signin/page/infoV3", {"client": "app"})
                    res2 = (r2 or {}).get("result") or {}
                    got = res2.get("total")
                    if _signed_of(res2):
                        ok, sig = True, f"回查日历已签 {waited}s"
                        break
                    if self.beans is not None and got is not None and got > self.beans:
                        ok, sig = True, f"回查余额 {self.beans}→{got}"
                        break
            if ok:
                log.log(f"  ✅ 签到完成（+{res.get('signInPoints')} 豆｜连签 {res.get('signCount')} 天｜{sig}）")
            else:
                log.log(f"  ⚠️ 签到未生效（回查 {waited}s 仍未确认，下轮会再试）：{res}")
        elif r and r.get("code") in (614, 615):
            log.log("  ⚠️ 签到失败（614/615 风控），稍后重试")
        else:
            log.log(f"  ❌ 签到失败：{r}")
    
    async def sign_double(self):
        r = await self._yget("/signin/page/multiple", {"client": "app"})
        if r and r.get("code") == 0:
            res = r.get("result") or {}
            log.log(f"  ✖️2️⃣ 签到翻倍领取成功：+{res.get('cloudCount')} 豆")
        elif r and "已领取" in str(r.get("msg")):
            log.log(f"  ✖️2️⃣ 签到翻倍：{r.get('msg')} ⏭️")
        else:
            log.log(f"  ✖️2️⃣ 签到翻倍：{r}")
    
    async def claim_records(self):
        """
        infoV3.receiveList 三类：
          cloudType=0 → POST /signin/page/receiveV3 {client, cloudId=recordId, cloudType}
          cloudType=1 → GET  /signin/page/receiveTaskExpansion?acceptDate=YYYYMM（膨胀/月度）
          cloudType=2 → 下月可领取，跳过
        """
        if not self.info:
            await self.query_status()
        items = self.info.get("receiveList") or []
        if not items:
            log.log("  🫘 待领取记录：无 ⏭️")
            return 0
        total = pending = lock_streak = 0
        for it in items:
            ct, num = it.get("cloudType"), int(it.get("cloudNum") or 0)
            if ct == 2:
                log.log(f"  🫘 {num} 豆：下月可领取 ⏭️")
                continue
            if ct == 1:
                date = it.get("acceptDate") or datetime.now().strftime("%Y%m")
                rr = await self._yget("/signin/page/receiveTaskExpansion", {"acceptDate": date})
                if not (rr and rr.get("code") == 0):
                    rr = await self._mget(f"/market/signin/page/receiveTaskExpansion?acceptDate={date}")
                if rr and rr.get("code") == 0:
                    out = rr.get("result")
                    got = out.get("cloudCount") if isinstance(out, dict) else out
                    log.log(f"  🫘 膨胀/月度奖励领取成功：{got}（{date}）")
                    total += num
                else:
                    log.log(f"  🫘 膨胀/月度奖励领取失败：{rr}")
                continue
            rr = None
            if not DEVICE_TOKEN and total == 0 and pending == 0:
                log.log("  ⚠️ 未配置 ydyp_device_token：领取记录豆会被判「未知设备」回 614，")
                log.log("     按脚本头「这些值怎么拿到」抓一次填上即可（同账号实测补上即成功）")
            tries = 1 if lock_streak >= 2 else 3  # 连续锁定后不再逐笔重试，节省运行时间
            for attempt in range(1, tries + 1):
                rr = await self._ypost("/signin/page/receiveV3",
                                       {"client": "app", "cloudId": it.get("recordId"), "cloudType": ct},
                                       dev=True)
                if rr and rr.get("code") == 0:
                    break
                if (rr or {}).get("code") not in (614, 615):
                    break
                if attempt < tries:
                    await asyncio.sleep(3 * attempt)
            if rr and rr.get("code") == 0:
                lock_streak = 0
                got = (rr.get("result") or {}).get("receive") or num
                log.log(f"  🫘 领取 {got} 豆 ✅（recordId={it.get('recordId')}）")
                total += int(got or 0)
            else:
                pending += num
                lock_streak += 1
                log.log(f"  🫘 领取失败（{num} 豆, recordId={it.get('recordId')}, code={(rr or {}).get('code')}）："
                        f"{(rr or {}).get('msg')}"
                        + ("｜614/615=设备未登记或风控锁定（检查 ydyp_device_token），下次运行自动重试"
                           if (rr or {}).get("code") in (614, 615) else ""))
            await asyncio.sleep(random.uniform(0.8, 1.6))
        if total:
            log.log(f"  🫘 记录豆合计领取：+{total}")
        if pending:
            log.log(f"  🫘 暂未领到：{pending} 豆（服务端锁定，稍后/下次运行重试）")
        return total
    
    async def task_list(self):
        self.user_domain_id = self.extract_user_domain_id(self.jwt)
        r = await self._ypost("/signin/task/taskListV3",
                              {"marketname": MARKET_NAME, "client": 1, "clientVersion": CLIENT_VERSION})
        tasks = {t["id"]: dict(t) for t in ((r or {}).get("result") or []) if t.get("id") is not None}
        for group in ("beiyong1", "cloudEmail", "time", "day", "month"):
            for t in await self.cloud_tasks_v2(group):
                tid = t.get("id")
                if tid is None:
                    continue
                # V2 补任务和步骤元数据，V3 的完成状态与进度优先。
                tasks[tid] = {**t, "groupid": group, **tasks.get(tid, {})}
        clicked = skipped = gained = 0
        try:
            for tid, t in tasks.items():
                if t.get("groupid") in ("hidden", "hiddenabc") and tid not in (106, 522, 434, 585, 587, 588, 589):
                    continue
                if t.get("state") == "FINISH":
                    skipped += 1
                    continue
                try:
                    clicked += bool(await self.complete_cloud_task(t))
                except Exception as error:
                    log.log(f"任务 {tid} 执行失败，继续其他任务：{error}")
                    clicked += 1
                await asyncio.sleep(random.uniform(1.0, 2.0))
            for tid, t in tasks.items():
                gained += await self._claim_task(tid, re.sub(r"<[^>]+>", "", t.get("name") or "")) or 0
        finally:
            await self.trash_cloud_files(list(self.created_files))
        log.log(f"任务处理：执行 {clicked} 条｜已完成 {skipped} 条｜本次领到 {gained} 豆")
        return clicked
    
    async def settle_task_rewards(self):
        """任务奖励异步记账的补领（issue #50 根因，详见说明 10）。

        任务 state→FINISH 是即时的，奖励却要过一会儿才出现在 infoV3.receiveList（记录豆）里；
        旧版只在本轮开头领一次，于是「第一遍永远领不到、第二遍才行」。
        这里刷新状态 + 有限轮询，记账够快时当次领掉；就是不快也只是维持旧行为（下一轮定时任务补领）。
        """
        seen = {it.get("recordId") for it in ((self.info or {}).get("receiveList") or [])}
        elapsed = 0
        for wait in WAIT_SETTLE:
            await asyncio.sleep(wait)
            elapsed += wait
            await self.query_status(quiet=True)  # 只刷新 self.info，不打日志
            items = (self.info or {}).get("receiveList") or []
            fresh = [it for it in items
                     if it.get("recordId") not in seen and it.get("cloudType") != 2]
            if fresh:
                log.log(f"      ⏳ 任务奖励已记账（等待 {elapsed}s，{len(fresh)} 笔），立即补领")
                got = await self.claim_records()   # claim_records 直接用刚刷新的 self.info
                if got:
                    log.log(f"      🫘 本次补领 +{got} 豆")
                return got
        log.log(f"      ⏳ 任务奖励仍在服务端记账中（已等 {elapsed}s）：本轮不领，下一轮定时任务自动补领")
        return 0

    async def _click_task(self, task_id, name="", key="task"):
        r = await self._yget("/signin/task/click", {"key": key, "id": task_id})
        ok = bool(r and r.get("code") == 0)
        log.log(f"      {'✅' if ok else '⏭️'} {name[:20]}（id={task_id}）{'' if ok else '：' + str(r)}")
        return r
    
    async def _claim_task(self, task_id, name=""):
        """领取任务奖励（任务未完成时返回 result:0）"""
        r = await self._yget("/signin/page/receiveTask", {"taskId": task_id})
        if r and r.get("code") == 0 and (r.get("result") or 0) > 0:
            log.log(f"      🎁 「{name[:20]}」领取 {r['result']} 豆")
            return int(r["result"])
        return 0
    
    
    async def backup_cloud(self):
        """连续备份奖励 + 每月膨胀云朵"""
        info = await self._yget("/backupgift/info")  # 新域同值且更稳
        if not (info and info.get("code") == 0):
            info = await self._mget("/market/backupgift/info")
        state = ((info or {}).get("result") or {}).get("state")
        if state == 0:
            r = await self._mget("/market/backupgift/receive")
            if r and r.get("code") == 0:
                res = r.get("result")
                got = res.get("result") if isinstance(res, dict) else res
                log.log(f"  ☁️ 连续备份奖励领取成功：{got} 豆")
            else:
                log.log(f"  ☁️ 连续备份奖励领取失败：{r}")
        elif state == 1:
            log.log("  ☁️ 连续备份奖励：本月已领 ⏭️")
        elif state is None:
            log.log(f"  ☁️ 连续备份奖励：接口返回异常 ⏭️ {info}")
        else:
            log.log(f"  ☁️ 连续备份奖励：本月未备份，暂无 ⏭️（state={state}）")
        
        exp = await self._mget("/market/signin/page/taskExpansion")
        res = (exp or {}).get("result") or {}
        if res.get("preMonthBackup") and not res.get("curMonthBackupTaskAccept"):
            accept_date = res.get("aeptDate") or datetime.now().strftime("%Y-%m-%d")
            r = await self._mget(f"/market/signin/page/receiveTaskExpansion?acceptDate={accept_date}")
            if r and r.get("code") == 0:
                out = r.get("result")
                got = out.get("cloudCount") if isinstance(out, dict) else out
                log.log(f"  ☁️ 膨胀云朵领取成功：{got}")
            else:
                log.log(f"  ☁️ 膨胀云朵：{r}")
        else:
            log.log("  ☁️ 膨胀云朵：暂无可领 ⏭️")
    
    async def notice_task(self):
        """开启 App 通知奖励（msgPushOn）"""
        r = await self._mget("/market/msgPushOn/task/status")
        res = (r or {}).get("result") or {}
        if not res:
            log.log(f"  ⏭️ 通知任务不可用：{r}")
            return
        log.log(f"  🔔 通知已开启 {res.get('onDuaration')} 天（累计 {res.get('total')} 天）")
        for t, st in ((1, res.get("firstTaskStatus")), (2, res.get("secondTaskStatus"))):
            if st == 2:  # 2 = 可领取
                rr = await self._req("POST", MARKET + "/market/msgPushOn/task/obtain",
                                     json={"type": t},
                                     headers=self._h({"Content-Type": "application/json"}))
                if rr and rr.get("code") == 0:
                    log.log(f"  🔔 通知任务{t} 领取成功：{rr.get('result')}")
                else:
                    log.log(f"  🔔 通知任务{t} 领取返回：{rr}")
    
    
    async def upload_file(self, count=1):
        """OSE 三步上传：getUploadUrl → PUT 原始字节 → file/complete。
        实测：传 1 个即把任务 106 推到 FINISH；但**不计入 522**（见 说明 5）。"""
        ok = fail = streak = 0
        total = max(1, count)
        stamp = datetime.now().strftime("%Y%m%d%H%M%S")
        for i in range(total):
            fname = "mock_%s_%02d.txt" % (stamp, i + 1)
            data = ("mcloud mock doc %s" % fname).encode()
            r = await self._ypost("/api/cloud/ose/activity/getUploadUrl",
                                  {"marketName": UPLOAD_MARKET, "fileName": fname, "fileSize": len(data)})
            res = (r or {}).get("result") or {}
            if not (r and r.get("code") == 0 and res.get("uploadUrl")):
                fail += 1
                streak += 1
                log.log(f"      📤 取上传地址失败（{i + 1}/{total}）：{(r or {}).get('msg') or r}")
                if streak >= 3:
                    log.log("      📤 连续失败 3 次，中止本批上传（疑似频控），下次运行继续")
                    break
                await asyncio.sleep(3)
                continue
            try:
                resp = await self.client.put(res["uploadUrl"], content=data,
                                             headers={"Content-Type": "application/octet-stream"})
            except Exception as e:
                fail += 1
                streak += 1
                log.log(f"      📤 PUT 异常（{i + 1}/{total}）：{e}")
                continue
            if resp.status_code not in (200, 201, 204):
                fail += 1
                streak += 1
                log.log(f"      📤 PUT 失败 HTTP {resp.status_code}（{i + 1}/{total}）")
                continue
            algo = (res.get("hashAlgorithm") or "SHA256").upper()
            ch = (hashlib.sha256(data).hexdigest() if algo == "SHA256"
                  else hashlib.md5(data).hexdigest())
            rr = await self._ypost("/api/cloud/ose/file/complete",
                                   {"uploadId": res.get("uploadId"), "fileId": res.get("fileId"),
                                    "contentHash": ch, "contentHashAlgorithm": res.get("hashAlgorithm") or "SHA256"})
            if rr and rr.get("code") == 0:
                ok += 1
                streak = 0
            else:
                fail += 1
                streak += 1
                log.log(f"      📤 完成上传失败（{i + 1}/{total}）：{rr}")
            if total > 5 and (i + 1) % 10 == 0:
                log.log(f"      📤 进度 {i + 1}/{total}（成功 {ok}｜失败 {fail}）")
            await asyncio.sleep(random.uniform(0.6, 1.2))
        if ok:
            log.log(f"      📤 本次上传 {ok} 个文件（失败 {fail}）")
        return ok
    
    async def create_cloud_file(self, prefix, extension="txt"):
        now = datetime.now(timezone(timedelta(hours=8)))
        file_name = f"{prefix}{now.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.{extension.lstrip('.')}"
        # shortcut: 沿用源脚本的 file/create 登记协议，进度不增长时需真实客户端上传。
        payload = {
            "contentHash": hashlib.sha256(b"0").hexdigest(),
            "contentHashAlgorithm": "SHA256", "contentType": "application/oct-stream",
            "fileRenameMode": "force_rename", "localCreatedAt": now.isoformat(timespec="milliseconds"),
            "name": file_name, "parallelUpload": True, "parentFileId": "/",
            "partInfos": [{"end": 1, "partNumber": 1, "partSize": 1, "start": 0}],
            "size": 1, "type": "file",
        }
        r = await self._req("POST", "https://personal-kd-njs.yun.139.com/hcy/file/create",
                            headers=self.build_cloud_file_headers(), json=payload)
        data = (r or {}).get("data") or {}
        if not (r and r.get("success") and data.get("fileId")):
            log.log(f"个人云创建文件失败：{(r or {}).get('message') or r}")
            return None
        self.created_files.append(data["fileId"])
        return {"fileId": data["fileId"], "fileName": data.get("fileName", file_name)}

    async def cloud_tasks_v2(self, group):
        r = await self._req("POST", H5 + "/market/signin/task/taskListV2",
                            headers=self._h({"Content-Type": "application/json;charset=UTF-8"}),
                            json={"marketname": MARKET_NAME, "clientVersion": CLIENT_VERSION, "group": group},
                            quiet=True)
        if not (r and r.get("code") == 0):
            log.log(f"V2 任务列表 {group} 不可用：{(r or {}).get('msg') or r}")
            return []
        return (r.get("result") or {}).get(group) or []

    async def query_cloud_task(self, task_id, group="time"):
        tasks = await self.cloud_tasks_v2(group)
        found = next((t for t in tasks if t.get("id") == task_id), None)
        if found:
            return found
        r = await self._ypost("/signin/task/taskListV3",
                              {"marketname": MARKET_NAME, "client": 1, "clientVersion": CLIENT_VERSION})
        return next((t for t in ((r or {}).get("result") or []) if t.get("id") == task_id), None)

    async def complete_cloud_task(self, task):
        tid = task.get("id")
        name = re.sub(r"<[^>]+>", "", task.get("name") or "")
        group = task.get("groupid")
        step_types = set(task.get("stepTypeSet") or [])
        step = int(task.get("currstep") or 0)
        if tid in (585, 587, 588, 589):
            if "click" in step_types and step == 0:
                r = await self._click_task(tid, name)
                if not (r and r.get("code") == 0):
                    return False
            if tid == 585:
                ok = await self.complete_ai_camera_task()
            elif tid == 587:
                ok = await self.complete_mayday_memory_task(task)
            elif tid == 588:
                ok = await self.complete_travel_guide_ai_task()
            else:
                ok = await self.complete_holiday_nine_grid_task()
            refreshed = await self.query_cloud_task(tid, group or "beiyong1") or task
            state = "已完成" if refreshed.get("state") == "FINISH" else "已执行，待服务端确认" if ok else "需手动完成"
            log.log(f"{name}：{state}（进度 {refreshed.get('process', 0)}）")
            return True
        if tid == 434:
            refreshed = await self.complete_share_file_task(task)
            log.log(f"{name}：{'已完成' if refreshed and refreshed.get('state') == 'FINISH' else '分享已执行，待服务端确认' if refreshed else '需手动完成'}")
            return True
        if tid == 522:
            ok = await self.complete_monthly_upload_task(task)
            log.log(f"{name}：{'已完成' if ok else '进度未达标，需真实上传/PC 客户端累计'}")
            return True
        if tid == 106:
            await self._click_task(tid, name)
            if not await self.upload_file():
                await self.create_cloud_file("auto_upload_")
            return True
        if tid == 406:
            await self.notice_task()
            return True
        if group == "beiyong1":
            log.log(f"{name}：需手动完成")
            return False
        if tid == 409:
            keys = ["task2"] if step > 0 else ["task", "task2"]
        elif "stepTypeSet" not in task or ("click" in step_types and step == 0):
            keys = ["task"]
        else:
            log.log(f"{name}：需手动完成（进度 {task.get('process', 0)}）")
            return False
        for key in keys:
            r = await self._click_task(tid, name, key=key)
            if not (r and r.get("code") == 0):
                break
        return True

    @staticmethod
    def extract_user_domain_id(jwt_token):
        try:
            payload = jwt_token.split('.')[1]
            payload += '=' * (-len(payload) % 4)
            data = json.loads(base64.urlsafe_b64decode(payload).decode())
            sub = data.get('sub', '')
            if isinstance(sub, str):
                sub = json.loads(sub)
            return sub.get('userDomainId', '')
        except (IndexError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            return ''

    def build_cloud_file_headers(self):
        """云盘文件操作请求头：沿用 v5.0.3 已验证可用的上传头，避免 00010014"""
        return {'x-yun-op-type': '1', 'x-yun-sub-op-type': '100', 'x-yun-api-version': 'v1', 'x-yun-client-info': '6|127.0.0.1|1|12.1.0|realme|RMX5060|BCFF2BBA6881DD8E4971803C63DDB5E4|02-00-00-00-00-00|android 15|1264X2592|zh||||032|0|', 'x-yun-app-channel': '10000023', 'Authorization': self.authorization, 'Content-Type': 'application/json; charset=UTF-8', 'User-Agent': 'okhttp/4.12.0', 'Host': 'personal-kd-njs.yun.139.com', 'Connection': 'Keep-Alive'}

    def build_share_headers(self):
        """分享文件请求头：沿用 v5.0.3 已验证可用的分享头"""
        return {'Authorization': self.authorization, 'x-yun-api-version': 'v1', 'x-yun-app-channel': '10000023', 'x-yun-client-info': f'||9|{CLIENT_VERSION}|Chrome|143.0.7499.146|codextestshare||Windows 10||zh-CN|||Q2hyb21l||', 'x-yun-module-type': '100', 'x-yun-svc-type': '1', 'x-SvcType': '1', 'x-yun-channel-source': '10000023', 'x-huawei-channelSrc': '10000023', 'Content-Type': 'application/json;charset=UTF-8', 'CMS-DEVICE': 'default', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36', 'Referer': 'https://yun.139.com/shareweb/', 'Origin': 'https://yun.139.com'}

    async def trash_cloud_files(self, file_ids):
        if not file_ids:
            return True
        response = await self._req('POST', 'https://personal-kd-njs.yun.139.com/hcy/recyclebin/batchTrash', headers=self.build_cloud_file_headers(), json={'fileIds': file_ids})
        if not response:
            log.log('清理上传文件失败: 接口无响应')
            return False
        if response.get('success'):
            self.created_files[:] = [fid for fid in self.created_files if fid not in file_ids]
            return True
        log.log(f"清理上传文件失败: {response.get('message', '未知错误')}")
        return False

    async def complete_share_file_task(self, task):
        share_file = await self.create_cloud_file('auto_share_')
        if not share_file:
            log.log('分享文件失败: 创建临时文件失败')
            return None
        try:
            response = await self._req('POST', 'https://yun.139.com/orchestration/personalCloud-rebuild/outlink/v1.0/getOutLink', headers=self.build_share_headers(), json={'getOutLinkReq': {'subLinkType': 0, 'encrypt': 1, 'coIDLst': [share_file.get('fileId')], 'caIDLst': [], 'pubType': 1, 'dedicatedName': share_file.get('fileName', ''), 'period': 1, 'periodUnit': 1, 'viewerLst': [], 'extInfo': {'isWatermark': 0, 'shareChannel': '3001'}, 'commonAccountInfo': {'account': self.account, 'accountType': 1}}}, tries=1)
        finally:
            await self.trash_cloud_files([share_file.get('fileId')])
        data = response.get('data', {}) if response else {}
        result = data.get('result', {}) or data.get('getOutLinkRes', {})
        outlinks = result.get('getOutLinkResSet') or []
        success = False
        if response:
            success = response.get('success') and result.get('resultCode') == '0' or (str(response.get('code')) == '0' and bool(outlinks))
        if not success:
            if response:
                msg = result.get('resultDesc') or response.get('message') or response.get('msg', '未知错误')
            else:
                msg = '接口无响应'
            log.log(f'分享文件失败: {msg}')
            return None
        return await self.query_cloud_task(task.get('id', 434), 'month') or task

    def build_ai_headers(self, use_client_info=False):
        """AI相机请求头，与主UA保持一致"""
        device_id = DEVICE_TOKEN or self.device_id
        headers = {'Connection': 'keep-alive', 'sec-ch-ua-platform': '"iOS"', 'Authorization': self.authorization, 'x-yun-api-version': 'v1', 'x-yun-tid': str(uuid.uuid4()), 'sec-ch-ua': '"Not A(Brand";v="8", "Chromium";v="130", "Mobile Safari";v="130"', 'sec-ch-ua-mobile': '?1', 'X-Requested-With': 'com.chinamobile.mcloud', 'Origin': 'https://frontend.mcloud.139.com', 'Referer': 'https://frontend.mcloud.139.com/', 'User-Agent': UA, 'Content-Type': 'application/json', 'Sec-Fetch-Site': 'same-site', 'Sec-Fetch-Mode': 'cors', 'Sec-Fetch-Dest': 'empty', 'Accept-Encoding': 'gzip, deflate, br, zstd', 'Accept-Language': 'zh,zh-CN;q=0.9,en-US;q=0.8,en;q=0.7'}
        if use_client_info:
            headers['Accept'] = 'text/event-stream'
            headers['x-yun-client-info'] = f"4||1|{CLIENT_VERSION}|Apple|iPhone 16 Pro|{device_id.lstrip('B')}|iOS 18.7|||||"
            headers['x-yun-app-channel'] = '101'
            return headers
        headers['Accept'] = '*/*'
        headers['x-DeviceInfo'] = f"||36|{CLIENT_VERSION}|Apple|iPhone 16 Pro|{device_id.lstrip('B')}|iOS 18.7|||||"
        return headers

    def encrypt_ai_tool_account(self):
        from Crypto.Cipher import AES
        from Crypto.Util.Padding import pad
        cipher = AES.new(AI_TOOL_ACCOUNT_AES_KEY.encode('utf-8'), AES.MODE_CBC, AI_TOOL_ACCOUNT_AES_IV.encode('utf-8'))
        encrypted = cipher.encrypt(pad(self.account.encode('utf-8'), AES.block_size))
        raw = AI_TOOL_ACCOUNT_AES_IV + base64.b64encode(encrypted).decode('utf-8')
        return base64.b64encode(raw.encode('utf-8')).decode('utf-8')

    def build_ai_tool_ad_headers(self):
        return {'Authorization': self.authorization, 'User-Agent': UA, 'Accept': 'application/json, text/plain, */*', 'Content-Type': 'application/json', 'Origin': 'https://yun.139.com', 'Referer': 'https://yun.139.com/aiTools/', 'x-yun-tid': str(uuid.uuid4())}

    def get_ai_camera_sample_base64(self):
        sample_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'assets', 'ai_camera_sample.jpg')
        if not os.path.exists(sample_path):
            return ''
        with open(sample_path, 'rb') as file:
            return f'data:image/jpg;base64,{base64.b64encode(file.read()).decode()}'

    @staticmethod
    def is_ai_chat_success(text):
        payloads = []
        for line in (text or '').splitlines():
            if line.startswith('data:'):
                payloads.append(line[5:].strip())
        if not payloads and text:
            payloads.append(text.strip())
        for payload in payloads:
            if not payload or payload == '[DONE]':
                continue
            try:
                data = json.loads(payload)
            except ValueError:
                continue
            if isinstance(data, dict) and (data.get('success') or data.get('code') == '0000'):
                return True
        return False

    async def complete_ai_camera_task(self):
        if not self.user_domain_id:
            log.log('AI相机任务失败: 缺少用户信息')
            return False
        image_data = self.get_ai_camera_sample_base64()
        if not image_data:
            log.log('AI相机任务失败: 缺少样图')
            return False
        recognize_payload = json.dumps({'channelId': '101', 'userId': self.user_domain_id, 'recognizeType': '1', 'base64': image_data, 'sendType': '2', 'imageExt': 'jpg', 'uploadToCloud': True, 'timeout': 30000}, ensure_ascii=False, separators=(',', ':'))
        recognize_data = await self._req('POST', 'https://ai.yun.139.com/api/image/aiRecognize', headers=self.build_ai_headers(), content=recognize_payload)
        if not recognize_data:
            log.log('AI相机识图失败: 接口无响应')
            return False
        if not recognize_data.get('success'):
            log.log(f"AI相机识图失败: {recognize_data.get('message', '未知错误')}")
            return False
        recognize_result = recognize_data.get('data') or {}
        file_id = recognize_result.get('fileId')
        if not file_id:
            log.log('AI相机识图失败: 缺少文件ID')
            return False
        task_id = str(recognize_result.get('taskId') or int(time.time() * 1000))
        file_name = f'{int(task_id) + 1}.jpeg' if task_id.isdigit() else f'{task_id}.jpeg'
        input_time = datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='milliseconds')
        chat_payload = json.dumps({'userId': self.user_domain_id, 'sessionId': '', 'applicationType': 'chat', 'applicationId': '', 'sourceChannel': '101', 'dialogueInput': {'dialogue': '？', 'prompt': '', 'inputTime': input_time, 'enableForceLlm': False, 'enableForceNetworkSearch': True, 'enableModelThinking': False, 'enableAllNetworkSearch': False, 'enableKnowledgeAndNetworkSearch': False, 'enableRegenerate': False, 'versionInfo': {'h5Version': '2.7.6'}, 'extInfo': '{}', 'sortInfo': {}, 'toolSetting': {'imageToolSetting': {'enableLlmDescribe': True}}, 'attachment': {'attachmentTypeList': [3], 'fileList': [{'fileId': file_id, 'name': file_name}]}}}, ensure_ascii=False, separators=(',', ':'))
        try:
            chat_response = await self.client.request('POST', 'https://ai.yun.139.com/api/outer/assistant/chat/v2/add', headers=self.build_ai_headers(use_client_info=True), content=chat_payload)
            chat_response.raise_for_status()
        except httpx.HTTPError as error:
            log.log(f'AI 对话请求失败：{error}')
            return False
        if chat_response is None:
            log.log('AI相机对话失败: 接口无响应')
            return False
        if self.is_ai_chat_success(chat_response.text):
            return True
        try:
            chat_data = chat_response.json()
        except ValueError:
            chat_data = None
        if chat_data and (chat_data.get('success') or chat_data.get('code') == '0000'):
            return True
        if chat_data:
            log.log(f"AI相机对话失败: {chat_data.get('message') or chat_data.get('msg', '未知错误')}")
            return False
        log.log('AI相机对话失败: 响应解析失败')
        return False

    async def complete_travel_guide_ai_task(self):
        if not self.user_domain_id:
            log.log('出行攻略问AI失败: 缺少用户信息')
            return False
        input_time = datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='milliseconds')
        chat_payload = json.dumps({'userId': self.user_domain_id, 'sessionId': '', 'applicationType': 'chat', 'applicationId': '', 'sourceChannel': '101', 'dialogueInput': {'dialogue': '给我一份五一出行攻略', 'prompt': '', 'inputTime': input_time, 'enableForceLlm': False, 'enableForceNetworkSearch': True, 'enableModelThinking': False, 'enableAllNetworkSearch': False, 'enableKnowledgeAndNetworkSearch': False, 'enableRegenerate': False, 'versionInfo': {'h5Version': '2.7.6'}, 'extInfo': '{}', 'sortInfo': {}, 'toolSetting': {'imageToolSetting': {'enableLlmDescribe': True}}, 'attachment': {}}}, ensure_ascii=False, separators=(',', ':'))
        try:
            chat_response = await self.client.request('POST', 'https://ai.yun.139.com/api/outer/assistant/chat/v2/add', headers=self.build_ai_headers(use_client_info=True), content=chat_payload)
            chat_response.raise_for_status()
        except httpx.HTTPError as error:
            log.log(f'AI 对话请求失败：{error}')
            return False
        if chat_response is None:
            log.log('出行攻略问AI失败: 接口无响应')
            return False
        response_text = chat_response.text or ''
        if chat_response.status_code == 200 and (not response_text.strip()):
            return True
        if self.is_ai_chat_success(response_text):
            return True
        try:
            chat_data = chat_response.json()
        except ValueError:
            chat_data = None
        if chat_data and (chat_data.get('success') or chat_data.get('code') == '0000'):
            return True
        if chat_data:
            log.log(f"出行攻略问AI失败: {chat_data.get('message') or chat_data.get('msg', '未知错误')}")
            return False
        log.log('出行攻略问AI失败: 响应解析失败')
        return False

    async def complete_monthly_upload_task(self, task):
        target_count = 100
        current_process = int(task.get('process') or 0)
        for attempt in range(3):
            remaining = max(0, target_count - current_process)
            if remaining == 0:
                return True
            log.log(f"-{('开始' if attempt == 0 else '继续')}补上传进度: 当前{current_process}/{target_count}，还需{remaining}次")
            success = 0
            for _ in range(remaining):
                if await self.create_cloud_file('auto_upload_'):
                    success += 1
                await asyncio.sleep(0.2)
            if success:
                log.log(f'-批量上传完成: {success}次')
            refreshed_task = await self.query_cloud_task(task.get('id', 522), 'time')
            if not refreshed_task:
                return False
            refreshed_process = int(refreshed_task.get('process') or 0)
            if refreshed_task.get('state') == 'FINISH' or refreshed_process >= target_count:
                return True
            if refreshed_process <= current_process:
                log.log(f'-月上传任务进度: {refreshed_process}/{target_count}')
                return False
            current_process = refreshed_process
        log.log(f'-月上传任务进度: {current_process}/{target_count}')
        return False

    async def complete_mayday_memory_task(self, task):
        target_count = 10
        task_id = task.get('id', 587)
        current_process = int(task.get('process') or 0)
        remaining = max(0, target_count - current_process)
        if remaining == 0:
            return True
        log.log(f'-开始补五一回忆上传: 当前{current_process}/{target_count}，还需{remaining}张')
        success = 0
        for _ in range(remaining):
            if await self.create_cloud_file('auto_mayday_', extension='jpg'):
                success += 1
        if success:
            log.log(f'-五一回忆上传完成: {success}张')
            await self._click_task(task_id)
        refreshed_task = await self.query_cloud_task(task_id, 'beiyong1')
        if not refreshed_task:
            return False
        refreshed_process = int(refreshed_task.get('process') or 0)
        if refreshed_task.get('state') == 'FINISH' or refreshed_process >= target_count:
            return True
        log.log(f'-五一回忆任务进度: {refreshed_process}/{target_count}')
        return False

    async def complete_holiday_nine_grid_task(self):
        # shortcut: 源脚本只获取模板并登记任务，服务端不认可时需 App 实际生成图片。
        try:
            encrypted_account = self.encrypt_ai_tool_account()
        except ImportError:
            log.log('假期九宫格模板任务失败: 缺少加密依赖')
            return False
        template_data = await self._req('POST', 'https://ad.mcloud.139.com/advertapi/adv-config/adv-config/AdInfoFilter/getAdInfos', headers=self.build_ai_tool_ad_headers(), json={'account': encrypted_account, 'adpostid': '66340', 'channel': '10000023', 'version': '10.5.0', 'client': 'iphone'})
        if not template_data:
            log.log('假期九宫格模板任务失败: 模板接口无响应')
            return False
        if str(template_data.get('returnCode')) != '0':
            log.log(f"假期九宫格模板任务失败: {template_data.get('returnMsg', '未知错误')}")
            return False
        click_data = await self._click_task(589)
        if click_data and str(click_data.get('code')) == '0':
            return True
        msg = click_data.get('msg', '未知错误') if click_data else '接口无响应'
        log.log(f'假期九宫格模板任务失败: {msg}')
        return False

    async def poke_cloud(self):
        completed = 0
        for _ in range(15):
            r = await self._click_task(319, "戳一戳")
            if not (r and r.get("code") == 0):
                break
            completed += 1
            await asyncio.sleep(0.2)
        return completed

    async def email_tasks(self):
        r = await self._mget("/market/signin/task/taskList?marketname=newsign_139mail")
        if not (r and r.get("code") == 0):
            log.log(f"139 邮箱任务不可用：{(r or {}).get('msg') or r}")
            return 0
        clicked = 0
        for task in ((r.get("result") or {}).get("month") or []):
            tid = task.get("id")
            if tid is None or tid in (1004, 1005, 1015, 1020) or task.get("state") == "FINISH":
                continue
            name = re.sub(r"<[^>]+>", "", task.get("name") or "")
            result = await self._mget(f"/market/signin/task/click?key=task&id={tid}")
            log.log(f"139 邮箱 {name}：{result}")
            clicked += bool(result and result.get("code") == 0)
            await asyncio.sleep(2)
        return clicked

    async def legacy_lottery(self):
        info = await self._mget("/market/playoffic/drawInfo")
        if not (info and info.get("msg") == "success"):
            log.log(f"老抽奖不可用：{(info or {}).get('msg') or info}")
            return
        if int((info.get("result") or {}).get("surplusNumber") or 0) <= 49:
            return
        r = await self._mget("/market/playoffic/draw")
        if r and r.get("code") == 0:
            log.log(f"老抽奖获得：{(r.get('result') or {}).get('prizeName')}")
        else:
            log.log(f"老抽奖未领取：{(r or {}).get('msg') or r}（602 表示活动已结束）")
    
    async def live_room_flower(self):
        """直播间小红花：首次参与直接赠花（实测领到 10 朵）"""
        info = await self._yget("/liveRoomFeedback/user/info")
        res = (info or {}).get("result") or {}
        if not res:
            log.log(f"    🌸 直播间：接口不可用 ⏭️")
            return
        if res.get("hasNotReceivedRedFlower") == 1:
            r = await self._ypost("/liveRoomFeedback/firstParticipate/give")
            out = (r or {}).get("result") or {}
            if r and r.get("code") == 0:
                log.log(f"    🌸 首参领红花：{out.get('prizeName')}（{out.get('flowerNum')} 朵）✅")
            else:
                log.log(f"    🌸 首参领红花失败：{r}")
        else:
            log.log(f"    🌸 直播间红花：已领 ⏭️（库存 {res.get('flowerCnt')}｜有效期 {res.get('redFlowerValidDate')}）")
        rf = await self._yget("/liveRoomFeedback/redFlower/queryRevivalFlowers")
        if rf and rf.get("code") == 0:
            log.log(f"    🌸 可复活红花：{rf.get('result')}")
    
    async def annual_reward(self):
        """年度回馈：开福袋抽奖（与新春礼同源接口 /simple/springgift/*，活动窗口至 2026-12-31；有次数才抽）"""
        tl = await self._yget("/simple/springgift/getTaskList")
        reg_ok = True
        for t in ((tl or {}).get("result") or []):
            if t.get("complete") or not t.get("needRegister") or not reg_ok:
                continue
            r = await self._ypost("/simple/springgift/registerTask", {"mark": t.get("id")}, quiet=True)
            if r is None:  # 该路由服务端未部署（404），后续不再尝试
                reg_ok = False
                log.log("    🧧 年度回馈：任务登记接口未部署（registerTask 404），跳过登记 ⏭️")
        cnt = await self._yget("/simple/springgift/getLotteryCount")
        try:
            n = int((cnt or {}).get("result") or 0)
        except (TypeError, ValueError):
            n = 0
        if n <= 0:
            log.log("    🧧 年度回馈：无抽奖次数 ⏭️")
            return
        log.log(f"    🧧 年度回馈：可用 {n} 次")
        for _ in range(min(n, 6)):
            r = await self._ypost("/simple/springgift/lotteryPrize", {"isClient": True})
            name = ((r or {}).get("result") or {}).get("prizeName")
            log.log(f"        {'🎉 抽中：' + str(name) if name else '⏭️ 本次未中奖'}")
            await asyncio.sleep(random.uniform(1.0, 2.0))
    
    async def token_pk(self):
        """TokenPK：阶段进度奖励 + 抽奖机会"""
        home = await self._yget("/tokenpk/toplist/progress/queryHome")
        res = (home or {}).get("result") or {}
        if not res:
            log.log("    🏆 TokenPK：活动未开 ⏭️")
            return
        used = res.get("usedToken")
        stages = res.get("rewardStages") or []
        log.log(f"    🏆 TokenPK：已用 {used} token｜{len(stages)} 个阶段")
        for st in stages:
            if st.get("status") == 1:  # 1 = 可领取
                r = await self._ypost("/tokenpk/toplist/progress/receiveReward",
                                      {"phaseNo": st.get("phaseNo")})
                log.log(f"        🏆 阶段 {st.get('phaseNo')}（{st.get('threshold')}）奖励：{r}")
        await self._ypost("/tokenpk/toplist/progress/autoReceiveLotteryChance")
        ch = await self._yget("/tokenpk/toplist/progress/queryRemainChance")
        try:
            c = int((ch or {}).get("result") or 0)
        except (TypeError, ValueError):
            c = 0
        for _ in range(c):
            r = await self._ypost("/tokenpk/toplist/progress/lottery")
            log.log(f"        🎟️ TokenPK 抽奖：{(r or {}).get('result')}")
            await asyncio.sleep(1.2)
    
    async def mcloud_day(self):
        """云盘日（会员日，每月 16 号 10:00 开窗）：盲盒 + 礼品。
        未开窗时 /mcloudday/gift/* 与 /mcloudday/blindbox/* 整体 404（活动按窗口上下线），
        所以先看 online 再动作——否则会像旧版那样逐条试探 20+ 个礼品、刷一屏 404。"""
        info = await self._yget("/mcloudday/common/activityInfo", {"marketName": "mCloudDay"})
        res = (info or {}).get("result") or {}
        if not res:
            log.log("    📦 云盘日：接口不可用 ⏭️")
            return
        online = bool(res.get("online"))
        log.log("    📦 云盘日：主活动 %s｜盲盒 %s｜额外礼 %s｜邀请 %s"
                % (online, res.get("blindboxOnline"), res.get("extGiftOnline"),
                   res.get("inviteOnline")))
        if not online:
            eta = ""
            try:
                left = float(res.get("countDownTimeStamp") or 0) / 3600000.0
                eta = f"，约 {left:.1f} 小时后开窗" if left > 0 else ""
            except (TypeError, ValueError):
                eta = ""
            log.log(f"    📦 云盘日未开窗（每月 16 号 10:00）{eta} ⏭️ 礼品/盲盒接口未开窗返回 404，已跳过")
            return
        if res.get("blindboxOnline"):
            li = await self._yget("/mcloudday/blindbox/lotteryInfo", quiet=True)
            lres = (li or {}).get("result") or {}
            try:
                n = int(lres.get("lotteryCount") or 0)
            except (TypeError, ValueError):
                n = 0
            if n <= 0:
                log.log("        🎁 盲盒：今日免费次数已用完 ⏭️")
            for _ in range(min(max(n, 0), 5)):
                # ⚠️ 抽奖必须「JSON body（client=1=App 端）+ isDeviceId 设备头」两者齐备，
                #    否则网关直接回 nginx 404（不是业务错误码）。2026-10-16 实测对照：
                #    POST {}                 -> 404
                #    POST {"client":"1"}+设备头 -> 200 {"code":0}（次数同步 -1）
                # 只重试连接类错误、读超时不重试，避免重复消耗次数（见 _req）。
                r = await self._ypost("/mcloudday/blindbox/lottery", {"client": "1"}, dev=True, quiet=True)
                if r and r.get("code") == 0:
                    prize = (r.get("result") or {}).get("prize") or {}
                    name = prize.get("prizeName") if isinstance(prize, dict) else prize
                    log.log(f"        🎁 盲盒：抽中 {name}" if name else "        🎁 盲盒：空盒（本次未中奖）")
                else:
                    log.log(f"        🎁 盲盒：{(r or {}).get('msg') or r}")
                await asyncio.sleep(random.uniform(1.2, 2.0))
            if lres.get("hasAnySurprisePrizeStock"):
                # 惊喜助力礼按邀请人数分档（inviteCount 1/4/10），未达门槛回 40001「未满足惊喜奖品条件」
                r = await self._ypost("/mcloudday/blindbox/receiveSurprisePrize",
                                      {"inviteCount": 1}, quiet=True)
                if r and r.get("code") == 0:
                    log.log(f"        🎁 惊喜礼：{r.get('result')}")
                else:
                    log.log(f"        🎁 惊喜礼：{(r or {}).get('msg') or r}（当前邀请 {lres.get('totalInviteCount', 0)} 人）")
        gl = await self._yget("/mcloudday/gift/list", quiet=True)
        gre = (gl or {}).get("result") or {}
        prizes = (gre.get("nationalPrizeList") or []) + (gre.get("provPrizeList") or [])
        stock = [p for p in prizes if p.get("hasStock") and not p.get("receiveFlag")]
        if not stock:
            # 限量礼品（totalCount/hasStock 由服务端放的量决定）；每月 16 号 10/12/15 点各放一波
            log.log(f"    📦 云盘日礼品：{len(prizes)} 项均无库存（限量已抢完）或已领 ⏭️")
            return
        got = []
        for p in stock:
            # 入参照 H5：{prizeId, smsCode, deviceId}。2026-10-16 实测（拿零库存奖品打，不消耗）：
            #   只发 {prizeId}（无论带不带设备头/令牌）-> nginx 404；补 smsCode 字段 -> 200 业务码
            #   ⇒ smsCode 必须存在（空码 = MD5("")），需短信的奖品会回 10004「验证码错误」
            r = await self._ypost("/mcloudday/gift/receive",
                                  {"prizeId": p.get("prizeId"), "smsCode": GIFT_SMS_CODE},
                                  dev=True, quiet=True)
            if r and r.get("code") == 0:
                got.append(str(p.get("prizeName")))
            else:
                m = str((r or {}).get("msg") or r)
                hint = "（该奖品要短信验证码，只能 App 内手领）" if ("验证" in m or "短信" in m) else ""
                log.log(f"        🎁 礼品「{p.get('prizeName')}」未领到：{m}{hint}")
            await asyncio.sleep(random.uniform(0.8, 1.5))
        log.log(f"    📦 云盘日礼品：成功 {len(got)}/{len(stock)} 件"
                + (f"（{'、'.join(got[:6])}{'…' if len(got) > 6 else ''}）" if got else ""))
    
    async def email_sms(self):
        """邮箱/短信联合活动：状态查询 + 奖励尝试（资格受限时返回 604）"""
        ti = await self._yget("/openemailsms-service/openEmailsms/getTaskInfo")
        res = (ti or {}).get("result") or {}
        if res:
            log.log("    📧 邮箱短信：任务一 %s｜任务二 %s"
                    % ((res.get("taskOneInfo") or {}).get("taskStatus"),
                       (res.get("taskTwoInfo") or {}).get("taskStatus")))
        r = await self._yget("/openemailsms-service/openEmailsms/reward")
        if r and r.get("code") == 0:
            log.log(f"    📧 邮箱短信奖励：{r.get('result')}")
        else:
            log.log(f"    📧 邮箱短信奖励：{(r or {}).get('msg')} ⏭️")
    
    async def activity_patrol(self):
        """活动巡检：逐个活动查状态，仅在有可领项时动作"""
        pats = (("签到翻倍", self.sign_double), ("直播间小红花", self.live_room_flower),
                ("年度回馈开福袋", self.annual_reward), ("TokenPK", self.token_pk),
                ("云盘日", self.mcloud_day), ("邮箱短信", self.email_sms))
        for name, fn in pats:
            try:
                await fn()
            except Exception as e:
                log.log(f"    ❌ {name} 异常：{e}")
            await asyncio.sleep(random.uniform(0.5, 1.2))
    
    async def run(self):
        log.log(f"========== 用户【{self.show_account}】 ==========")
        log.log(f"  📱 设备号 {self.device_id}｜UA {UA if len(UA) <= 72 else UA[:72] + '…'}"
                f"｜设备令牌 {'已配置 ✅' if DEVICE_TOKEN else '未配置 ⚠️（领记录豆会 614）'}")
        await self._refresh_authorization()
        if not await self.login():
            log.log("  ❌ 登录失败，跳过该账号")
            return
        begin = await self._balance()
        await self.query_status()
        log.log("──────── 签到 ────────")
        await self.sign_in()
        log.log("──────── 记录豆领取（签到/任务记录）────────")
        await self.claim_records()
        log.log("──────── 任务 ────────")
        clicked = await self.task_list()
        log.log("──────── 戳一戳 / 139邮箱任务 ────────")
        clicked += await self.poke_cloud()
        clicked += await self.email_tasks()
        if clicked:
            # 上传/点击类任务的奖励异步记账，跑完立即轮询补领（issue #50）
            await self.settle_task_rewards()
        log.log("──────── 连续备份奖励 ────────")
        await self.backup_cloud()
        log.log("──────── 通知任务 ────────")
        await self.notice_task()
        log.log("──────── 活动巡检 ────────")
        await self.activity_patrol()
        await self.legacy_lottery()
        await self.query_status(quiet=True)
        await self.claim_records()
        end = await self._balance()
        if begin is not None and end is not None:
            log.log(f"──────── 结束：AI豆 {begin} → {end}（+{end - begin}）────────")
        else:
            log.log(f"──────── 结束时 AI豆余额：{end} ────────")
        log.log("")


async def main():
    if not _require_ua():
        return
    cookies = get_env("ydyp_ck", "@")
    if not cookies:
        log.log("❌ 未配置环境变量 ydyp_ck")
        return
    for ck in cookies:
        worker = MobileCloudDisk(ck)
        try:
            await worker.run()
        finally:
            await worker.client.aclose()
    send_notification_message_collection(f"中国移动云盘签到通知 - {datetime.now().strftime('%Y/%m/%d')}")


async def check():
    """只读自检：不签到、不抽奖、不领豆"""
    if not _require_ua():
        return
    cookies = get_env("ydyp_ck", "@")
    if not cookies:
        log.log("❌ 未配置环境变量 ydyp_ck")
        return
    for ck in cookies:
        w = MobileCloudDisk(ck)
        try:
            log.log(f"========== 自检【{w.show_account}】 ==========")
            log.log("  📱 设备号：%s｜UA：%s｜设备令牌：%s" % (
                w.device_id, UA if len(UA) <= 72 else UA[:72] + "…",
                "已配置 ✅" if DEVICE_TOKEN else "未配置 ⚠️（签到/领记录豆会回 614）"))
            if not await w.login():
                log.log("  ❌ 凭据无效：请重新抓包更新 ydyp_ck")
                continue
            await w.query_status()
            items = w.info.get("receiveList") or []
            log.log(f"  🫘 待领取明细 {len(items)} 笔：")
            for it in items:
                log.log("      cloudType=%s %s 豆%s" % (it.get("cloudType"), it.get("cloudNum"),
                                                        f" acceptDate={it.get('acceptDate')}" if it.get(
                                                            "acceptDate") else
                                                        f" recordId={it.get('recordId')}" if it.get(
                                                            "recordId") else ""))
            r = await w._ypost("/signin/task/taskListV3",
                               {"marketname": MARKET_NAME, "client": 1, "clientVersion": CLIENT_VERSION})
            tasks = (r or {}).get("result") or []
            log.log(f"  🗂️ 任务 {len(tasks)} 条：")
            for t in tasks:
                log.log("      [%-10s] id=%-4s %-7s step=%-2s proc=%-4s %s" % (
                    t.get("groupid"), t.get("id"), t.get("state"), t.get("currstep"),
                    t.get("process"), (t.get("name") or "").strip()[:24]))
            b = await w._mget("/market/backupgift/info")
            log.log(f"  ☁️ 备份奖励：{b.get('result') if b else b}")
            p = await w._mget("/market/msgPushOn/task/status")
            log.log(f"  🔔 通知任务：{p.get('result') if p else p}")
            log.log("  🧭 活动状态（只读）：")
            for name, path, params in (("直播间", "/liveRoomFeedback/user/info", None),
                                       ("年度回馈抽奖次数", "/simple/springgift/getLotteryCount", None),
                                       ("TokenPK", "/tokenpk/toplist/progress/queryHome", None),
                                       ("云盘日", "/mcloudday/common/activityInfo", {"marketName": "mCloudDay"}),
                                       ("邮箱短信", "/openemailsms-service/openEmailsms/getTaskInfo", None)):
                rr = await w._yget(path, params)
                log.log("      %-14s code=%s %s" % (name, (rr or {}).get("code"),
                                                    json.dumps((rr or {}).get("result"), ensure_ascii=False)[:120]))
            log.log("  ✅ 自检完成（未做任何写操作）\n")
        finally:
            await w.client.aclose()


if __name__ == "__main__":
    if "--check" in sys.argv:
        asyncio.run(check())
    else:
        asyncio.run(main())

"""全局视觉常量。

customtkinter 的所有颜色都要 (浅色, 深色) 成对给, 才能跟随系统主题切换。
刻意做成模块级常量而不是类: 多个 View 要共用同一套色板, 放类里反而要跨类引用。
"""

# ---- 支付方式候选值: 与后端对接前先硬编码 ----
PAYMENT_METHODS = ['Apple Pay', '微信支付', '支付宝', '银行卡', '校园卡']

# 优惠券下拉的"不使用"哨兵值, 单独抽出来避免各处硬编码中文字面量
NO_COUPON = '不使用优惠券'

# ---- 色板 ----
PAGE_BG = ("#EFEFF4", "#141419")       # 整页底色, 比卡片更深一档, 衬托卡片浮起
TITLE_BAR_BG = ("#FFFFFF", "#23232B")  # 标题栏底色
SHADOW = ("#C7C7CC", "#07070A")        # 模拟阴影的实心色, 只在右下露出 2px
CARD_INFO_BG = ("#FFFFFF", "#1E1E24")  # 中性卡片
CARD_DINE_BG = ("#EAF2FB", "#1A2733")  # 冷色卡片, 用于区分区域
CARD_BORDER = ("#DCDCE1", "#33333D")   # 1px 描边, 强化卡片边界
TEXT_PRIMARY = ("#1C1C1E", "#F2F2F7")
TEXT_HEADING = ("#3A3A3C", "#C7C7CC")

# ---- 字号 ----
FONT_SIZE_TITLE = 36
FONT_SIZE_SECTION = 17
FONT_SIZE_BODY = 15
FONT_SIZE_BUTTON = 15

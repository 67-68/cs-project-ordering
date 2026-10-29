"""Visual constants.

customtkinter wants (light, dark) tuples so the palette follows the system theme.
Module level on purpose: several views share one palette.
"""

# hardcoded until there is a backend
PAYMENT_METHODS = ['Apple Pay', '微信支付', '支付宝', '银行卡', '校园卡']

# sentinel for "no coupon", so the literal is not scattered around
NO_COUPON = '不使用优惠券'

PAGE_BG = ("#EFEFF4", "#141419")        # slightly darker than cards
TITLE_BAR_BG = ("#FFFFFF", "#23232B")
SHADOW = ("#C7C7CC", "#07070A")         # fake shadow, 2px peek at bottom-right
CARD_INFO_BG = ("#FFFFFF", "#1E1E24")
CARD_DINE_BG = ("#EAF2FB", "#1A2733")   # cool tone, marks a different zone
CARD_BORDER = ("#DCDCE1", "#33333D")
TEXT_PRIMARY = ("#1C1C1E", "#F2F2F7")
TEXT_HEADING = ("#3A3A3C", "#C7C7CC")

FONT_SIZE_TITLE = 36
FONT_SIZE_SECTION = 17
FONT_SIZE_BODY = 15
FONT_SIZE_BUTTON = 15

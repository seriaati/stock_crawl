TWSE_IDS = "https://openapi.twse.com.tw/v1/opendata/t187ap03_L"  # 上市公司基本資料
TWSE_COMPANY_INFO = "https://openapi.twse.com.tw/v1/opendata/t187ap03_L"  # 上市公司基本資料
TWSE_DIVIDEND = "https://openapi.twse.com.tw/v1/exchangeReport/TWT48U_ALL"  # 上市公司除權息資料
TWSE_DAY_TRADE = (
    "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"  # 上市股票日成交資訊
)
TWSE_PUNISH = "https://openapi.twse.com.tw/v1/announcement/punish"  # 集中市場公布處置股票

TPEX_IDS = "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_quotes"  # 上櫃股票收盤行情
TPEX_DAY_TRADE = TPEX_IDS  # 上櫃股票日成交資訊
TPEX_COMPANY_INFO = "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O"  # 上櫃公司基本資料
TPEX_DIVIDEND = "https://www.tpex.org.tw/openapi/v1/tpex_exright_prepost"  # 上櫃公司除權息資料
TPEX_PUNISH = (
    "https://www.tpex.org.tw/openapi/v1/tpex_disposal_information"  # 上櫃處置有價證券資訊
)

FUBON_MAIN_FORCE = (
    "https://fubon-ebrokerdj.fbs.com.tw/z/zc/zco/zco_{id}_{day}.djhtm"  # 富邦證券主力進出明細
)
FUBON_MAIN_FORCE_DATE = "https://fubon-ebrokerdj.fbs.com.tw/z/zc/zco/zco.djhtm?a={id}&e={date}&f={date}"  # 富邦證券主力進出明細

MONEYDJ_STOCK_CATEGORY = "https://www.moneydj.com/Z/ZH/ZHA/ZHA.djhtm"  # 類股資料

TWSE_NEWS = "https://mops.twse.com.tw/mops/web/t05sr01_1"  # 上市公司公開資訊觀測站 - 即時重大訊息

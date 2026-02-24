from zalo_client import ZaloClient
import json
secret_key_b64 = 'YJKe4BtixnEaL+mSVrZH6Q=='
cookie_string = "__zi=3000.SSZzejyD2DyiZwEqqGn1pJ75lh39JHN1E8Yy_zm36zbxrAxraayVtJwRhV6II1gHDvYhlPHE7vKtaAwmDG.1; __zi-legacy=3000.SSZzejyD2DyiZwEqqGn1pJ75lh39JHN1E8Yy_zm36zbxrAxraayVtJwRhV6II1gHDvYhlPHE7vKtaAwmDG.1; app.event.zalo.me=2741210207746556291; _ga_3EM8ZPYYN3=GS2.2.s1768548662$o3$g0$t1768548662$j60$l0$h0; zpsid=O_aT.448370842.11.HW57mDHhYI5Eyp0xs6k98Q4O-nNWKxeMv5Ez4wNLY0pATYw6rJHWIBrhYI4; zpw_sek=djJL.448370842.a0.dNteIbD53XF9tRS9SaKE4oXdQtXnVonA6Gvh9n4nPsiz06zVU2XTHI4VHYK2U3CnBZIm4dvR4xJqH53wEYmE4m; _ga_YT9TMXZYV9=GS2.1.s1768657433$o1$g1$t1768657484$j9$l0$h0; _gid=GA1.2.131743463.1768657492; _gat=1; _ga=GA1.1.301146123.1768447803; _ga_RYD7END4JE=GS2.2.s1768657492$o2$g1$t1768657494$j58$l0$h0; _ga_YS1V643LGV=GS2.1.s1768657492$o3$g0$t1768657494$j58$l0$h0; _zlang=vn"
client = ZaloClient(secret_key_b64, cookie_string)
client.getUserByPhone("84923549252")

# data_get_friend_v1 = "P9B8fjSK9cLNGau20TE3N6xyG6YAyN4bU6popNTqEJDaQbfwrCdMqWBx2C+ov6n1Jx0dCHWDHbW1lSWLiB/VhVAA70/sXm7FUwNged4OiBVchzxCEJ6/DkzuSdd51rZhL8SuepItCgeHOw358QUxySnoQrQigx/MeZFM1//SFIh2tqVKRV2qlkr4lLOSak8VROmwAzoZYdAxBTTLP0GNycEwXzP4jjAG0ZeySQuQTaygwSRkA/GDcj1UEnHNEnK69Q2sqBxR/WO9B1sO9neG8YOXYx5Jye0kNsNXUrEX3GFWjkCEXU7K6X91eUetvOjFc4FmIhumN7G1u/3s4kVB2mWc7F2mS8D40EewLuTSCsK2gIsELfoUk/62FxxpC8Dap5rAnlmn3dLwGQxCtrb4/WleXs7SkKP7wuWjTk/gnsTWtQr/sLUTVws6iENMKHUppatzuzhi+Xp5MDWNBgWClRNfEV82rOAEVn6II272eDvNalF6IfZ6cIqV0J+kgoaVfpuPW5tiGCtYr/qHa6/W62Yz7YG+La0yDjfUvviHrgjXZwW+l7j03eHAZ2HiLfOqO9UrRBloW2iRyMgWEp5GGDNy7CDxl0BAHubryQ5+XcOqtrco/eG3KXud5P1O4Y0t"








# decode_v1 = client.decodeAES(data_get_friend_v1)
# print(decode_v1)
client.getUserByPhone("84923549252")
# client.sendTextMessage("3530844999012435089","Hello bạn ạdjsadjasidiakxas")
client.sendSmartMessage("84378571321","sdjasdjadjajsdja")
# import random
# import string
# import time

# def generate_random_uid(length=19):
#     """
#     Sinh ra chuỗi số ngẫu nhiên có độ dài cố định.
#     """
#     # Chọn ngẫu nhiên các ký tự từ 0-9 và ghép lại
#     return ''.join(random.choices(string.digits, k=length))

# print("=== BẮT ĐẦU SINH ID NGẪU NHIÊN ===")
# print("Nhấn Ctrl + C để dừng lại")

# try:
#     while True:
#         # 1. Sinh ID ngẫu nhiên
#         fake_uid = generate_random_uid(19)
        
#         # 2. In ra màn hình để kiểm tra
#         print(f"Generated ID: {fake_uid}")

#         # --- KHÔNG NÊN BỎ COMMENT DÒNG DƯỚI ĐỂ SPAM ---
#         response = client.sendTextMessage(fake_uid, "Hello bạn...") 
#         print("Response: ", response)
#         # -----------------------------------------------
#         try:
#             print(client.decodeAES(response['data']))
#         except:
#             continue
#         # 3. Nên có thời gian nghỉ (sleep) để tránh treo CPU
#         time.sleep(0.1) 

# except KeyboardInterrupt:
#     print("\nĐã dừng vòng lặp.")
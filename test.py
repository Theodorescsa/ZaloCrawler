from zalo_client import ZaloClient
import json
secret_key_b64 = "IWH4vYgF/FERJ4upjJJB9w=="
cookie_string = "__zi=3000.SSZzejyD2DyiZwEqqGn1pJ75lh39JHN1E8Yy_zm36zbxrAxraayVtJwRhV6II1gHDvYhlPHE7vKtaAwmDG.1; __zi-legacy=3000.SSZzejyD2DyiZwEqqGn1pJ75lh39JHN1E8Yy_zm36zbxrAxraayVtJwRhV6II1gHDvYhlPHE7vKtaAwmDG.1; _ga_RYD7END4JE=GS2.2.s1769050389$o5$g1$t1769050389$j60$l0$h0; _ga_YS1V643LGV=GS2.1.s1769050389$o6$g0$t1769050389$j60$l0$h0; _ga_YT9TMXZYV9=GS2.1.s1770878849$o5$g0$t1770878849$j60$l0$h0; _zlang=vn; _ga=GA1.2.301146123.1768447803; _gid=GA1.2.724648587.1770878871; _ga_3EM8ZPYYN3=GS2.2.s1770878871$o4$g0$t1770878871$j60$l0$h0; zpsid=gnmO.448370842.17.qUC0nHlgHg21Sl-w5-f6e6wPD9GlqdMNAz9oaW2hvjC5z-476ZOnBNBgHg0; zpw_sek=KCya.448370842.a0.B58HMsciDFhpD8tWIAmq-XAEKP5BbXQpFkG0Z33BSjKlwMQmNTb4a2FcTiCUaGdO5BTrMXgoALtEhUYDvCKq-W; app.event.zalo.me=2741210207746556291"
client = ZaloClient(secret_key_b64, cookie_string)
# client.getUserByPhone("84923549252")
data = "xrp4V4EI2xTQ9szRGqtisEZE+freMVJeP8oBWzb9JB7I1wQbKGplbkhclLcyWm4IXGfcOUtfTWg5c24iRAs2mZJ1pkxYkcBpmT8SSlUxxBs2V0hCGzqKMAXxkIa3/yI/"

decode_v1 = client.decodeAES(data)
print(decode_v1)
# client.getUserByPhone("84923549252")
# # client.sendTextMessage("3530844999012435089","Hello bạn ạdjsadjasidiakxas")
# client.sendSmartMessage("84378571321","sdjasdjadjajsdja")
# # import random
# # import string
# # import time

# # def generate_random_uid(length=19):
# #     """
# #     Sinh ra chuỗi số ngẫu nhiên có độ dài cố định.
# #     """
# #     # Chọn ngẫu nhiên các ký tự từ 0-9 và ghép lại
# #     return ''.join(random.choices(string.digits, k=length))

# # print("=== BẮT ĐẦU SINH ID NGẪU NHIÊN ===")
# # print("Nhấn Ctrl + C để dừng lại")

# # try:
# #     while True:
# #         # 1. Sinh ID ngẫu nhiên
# #         fake_uid = generate_random_uid(19)
        
# #         # 2. In ra màn hình để kiểm tra
# #         print(f"Generated ID: {fake_uid}")

# #         # --- KHÔNG NÊN BỎ COMMENT DÒNG DƯỚI ĐỂ SPAM ---
# #         response = client.sendTextMessage(fake_uid, "Hello bạn...") 
# #         print("Response: ", response)
# #         # -----------------------------------------------
# #         try:
# #             print(client.decodeAES(response['data']))
# #         except:
# #             continue
# #         # 3. Nên có thời gian nghỉ (sleep) để tránh treo CPU
# #         time.sleep(0.1) 

# # except KeyboardInterrupt:
# #     print("\nĐã dừng vòng lặp.")
from zalo_search_api import ZaloClient
import json
secret_key_b64 = 'JflN16+G2MnX2csb0rqgXg=='
cookie_string = "ozi=2000.SSZzejyD2DyiZwEqqGn1pJ75lh39JHN1E8Yy_zm36zbwrAxraqyOtpIUfVUMIX7VCj6bz9865zatrQNyD3ar.1; _ga_1J0YGQPT22=GS1.1.1743267239.1.1.1743267278.21.0.0; _gcl_au=1.1.1210773121.1762247361; _fbp=fb.1.1762247361146.837283859710473447; _ga_WSPJQT0ZH1=GS2.1.s1763113890$o2$g1$t1763113969$j60$l0$h0; _ga_NVN38N77J3=GS2.2.s1763113873$o3$g1$t1763113970$j27$l0$h0; _ga_E63JS7SPBL=GS2.1.s1763113859$o4$g1$t1763114099$j60$l0$h0; __zi=3000.SSZzejyD2DyiZwEqqGn1pJ75lh39JHN1E8Yy_zm36zbxrAxraayOt3EUhlQGGHEMDP6YkfP75f8rcQUtDG.1; __zi-legacy=3000.SSZzejyD2DyiZwEqqGn1pJ75lh39JHN1E8Yy_zm36zbxrAxraayOt3EUhlQGGHEMDP6YkfP75f8rcQUtDG.1; _ga_907M127EPP=GS2.1.s1766142174$o6$g1$t1766142174$j60$l0$h0; zoaw_sek=_jZY.1938785149.2.mkLFpMrjC2SGxhzKRMqm9srjC2TjRJ0dR8cPTGHjC2S; zoaw_type=0; _gid=GA1.2.1016670242.1767587780; _zlang=vn; _ga_3EM8ZPYYN3=GS2.2.s1767587784$o40$g0$t1767587784$j60$l0$h0; zpsid=PW4-.355636788.146.OoQoP7wS8zPA2X73SfmZrWllKULBgHNbIAiRxcNOgSvWWOHnVqGSZHUS8zO; zpw_sek=eR5i.355636788.a0.LH6EEYBtVw4MOKsq0_T_eLdL6ie0pLthH9ina1JSE9DlcIUJGOGTaL266Fb5oaA3N-mxAphfOWQ5zgUUUPv_eG; app.event.zalo.me=616744305790528006; _ga_YT9TMXZYV9=GS2.1.s1767603451$o8$g1$t1767603472$j39$l0$h0; _ga=GA1.1.759643980.1743071453; _ga_YS1V643LGV=GS2.1.s1767603476$o47$g0$t1767603477$j59$l0$h0; _ga_RYD7END4JE=GS2.2.s1767603477$o46$g1$t1767603477$j60$l0$h0"
client = ZaloClient(secret_key_b64, cookie_string)
data = "S/gN3xfJdnanaR3Q3TEzGUbHRB+NqiKYwJ+WyBekmcu66nF03MMGYpvGS1vbG2Nt4Xi14gENNhbN65h7oGqcgLBYjTo5yDb7Gfjg/H5rimrUauGWOTVs7w3ViGRU+cQHKTbxJVy3FoslVE6YF41NYvlSTBgTNehOl0cXDaGnx+U/MhtvIXPWm0uWWLfiNlaBl21O1d3470tVlrkw6yeGqmRpPxLprzF+6L1N30AqtKPUQ/D9/+2O/yvVPcu4AGaqSfUEmcqF1z+B553mx52SldT87SS211dpri0KgSAoIvPt79xdku/YyuIMBhLu3xJ+yayXvDNYZpgo8XkFRjBtcvWE0kkeuabi0Lo3OqCNyORLhyqhEr2IiJ6ioGO6LW53KJIckqwHR84eTZGT4q8z/+RnrjwBmsK8+ReEj1VNstVKl5zSZTOk+VforzyFJmMHmaNXnBHg4epERpolpf2YGQp+xsMjhzZzspUjv/P2IQzX1GKcfEoduYNRwapESU1lYu8yfrt46B6Ud/jVOTQSRxL3TRCgH3J1AIIX75hay24IBpk7E51N0A3hYItLfHM4Y/qvMyHu9bACXy6UFn5vovGFtdl26eBhZLNjqSpASDeCCl9UOXMIdNA0UzKg2A8AJRWnLNzeFrB8rO1t0zkBXIxV5p+pac/9a/LK16xMAZPB5olTq+uF39BhmYqj6vs+dubSeypejY8Vcb0LNarokwjRmTFDPIDW+Eit0Bb0dBLJdviVe90inrNNNlvsi0wY4MFRXl99sIawT2YCzM5ov4jAGbe1jVnTQ9J8ULS4gfsI3nJKclnwyse+GmvjSrKNy/NCfPCf9Cb5Cm1Je744QviTTZ/CuuBHUVLxzHYxLBqi+wd5dNT2BhhsvJYU6E2jwmA6GgcZA75D//CNEjVhN9ktNOHlK0uigN0Xdac6gE4m49i1lAOsN9QXo7R8MEfiuQdQyLaGh//ygGzQwpaRnIPiRcsXsDWo0WD4EK6/BucmZZiNH2vBB2GfnyNP7+57nGIYu+T7bW0Y4qWJq2ilA9RRor9ox1D8Ec41JvweF0yY/vFb1T1IObCXtfgU4j1Nb70RXEtVpPpVZNvusYQXgJJFE3TPXhyt3BovqFzwWh6HWNKR1cKCdLgT3Ai5nLDUEDx27raBLAyI0D0H7IbnXjG6NLDhprqfJERIUI3Qk3rQ9CZRPFLDXItXeOobISpS+QnUY208tJn2YQ7HrmvSHlFBn94iZb7aVranMVru0qWpc0hU0Tr2DubBvqrCVRMu"



decode = client.decodeAES(data)
print(decode)
# # list_friend = client.getRecommendedFriendsV2()
# # print(list_friend)
# print(decode)
# Ví dụ gửi tin nhắn cho cá nhân
# try:
#     result = client.sendZText(
#         client_id=1766136198020,
#         to_id="3990347544143465685",
#         message="Xin chào! Đây là tin nhắn tự động!",
#         is_group=False,
#         debug=True  # Bật debug để xem thông tin chi tiết
#     )
#     print("Kết quả:", result)
# except Exception as e:
#     print("Lỗi:", e)

# # Ví dụ gửi tin nhắn vào group
# try:
#     result = client.sendZText(
#         to_id="GROUP_ID_HERE",
#         message="Hello group!",
#         is_group=True,
#         visibility=0  # 0 = hiển thị cho tất cả
#     )
#     print("Gửi tin nhắn group thành công:", result)
# except Exception as e:
#     print("Lỗi:", e)

# UID của người cần lấy (ví dụ từ log của bạn)
# target_uid = "7921649594554906494"

# # Gọi API
# try:
#     # friend_pversion_map: "UID_0" để lấy thông tin mới nhất
#     result = client.getProfilesV2(
#         friend_pversion_map=[f"{target_uid}_0"], 
#         phonebook_version=1767504728 # Hoặc int(time.time())
#     )
#     print(json.dumps(result, indent=2, ensure_ascii=False))
# except Exception as e:
#     print(f"Lỗi: {e}")

# UID người nhận (Bạn bè)
# receiver_uid = "777081826066151257" 
# msg_content = "Xin chào, đây là tin nhắn test từ Python!"

# # --- SỬA Ở ĐÂY ---
# # Thay ZaloClient.sendTextMessage bằng client.sendTextMessage
# resp = client.sendTextMessage(
#     to_uid=receiver_uid,
#     message=msg_content
# )
# print("Gửi thành công:", json.dumps(resp, indent=2, ensure_ascii=False))

phone = "0919299589" # Số điện thoại người nhận
msg = "Chào bạn, mình nhắn từ tool Python qua SĐT!"

try:
    result = client.sendSmartMessage(phone, msg)
    print("Kết quả:", json.dumps(result, indent=2, ensure_ascii=False))
except Exception as e:
    print("Lỗi:", e)
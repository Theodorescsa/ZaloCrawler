from zalo_client import ZaloClient
import json
secret_key_b64 = 'hdqA2PcowjsqGRrtLtb2FA=='
cookie_string = "ozi=2000.SSZzejyD2DyiZwEqqGn1pJ75lh39JHN1E8Yy_zm36zbwrAxraqyOtpIUfVUMIX7VCj6bz9865zatrQNyD3ar.1; _ga_1J0YGQPT22=GS1.1.1743267239.1.1.1743267278.21.0.0; _gcl_au=1.1.1210773121.1762247361; _fbp=fb.1.1762247361146.837283859710473447; __zi=3000.SSZzejyD2DyiZwEqqGn1pJ75lh39JHN1E8Yy_zm36zbxrAxraayOt3EUhlQGGHEMDP6YkfP75f8rcQUtDG.1; __zi-legacy=3000.SSZzejyD2DyiZwEqqGn1pJ75lh39JHN1E8Yy_zm36zbxrAxraayOt3EUhlQGGHEMDP6YkfP75f8rcQUtDG.1; _ga_907M127EPP=GS2.1.s1766142174$o6$g1$t1766142174$j60$l0$h0; _ga_YT9TMXZYV9=GS2.1.s1767670825$o9$g0$t1767670825$j60$l0$h0; zoaw_sek=QkLN.1968800208.2.8wLFSLG-2NI4lr01L3u9T5G-2NHKFWbqLGMDA3q-2NG; zoaw_type=0; _ga_NVN38N77J3=GS2.2.s1767670840$o4$g1$t1767670845$j55$l0$h0; _ga_WSPJQT0ZH1=GS2.1.s1767670858$o3$g1$t1767670880$j38$l0$h0; _ga_E63JS7SPBL=GS2.1.s1767670834$o5$g1$t1767670883$j11$l0$h0; _ga=GA1.2.759643980.1743071453; _gid=GA1.2.1733340641.1767856264; _ga_RYD7END4JE=GS2.2.s1767856264$o47$g1$t1767856265$j59$l0$h0; _ga_YS1V643LGV=GS2.1.s1767856264$o48$g0$t1767856265$j59$l0$h0; _zlang=vn; _ga_3EM8ZPYYN3=GS2.2.s1767856272$o41$g0$t1767856272$j60$l0$h0; zpsid=zew_.355636788.155.DPQiPxWTvLUCYzT2j1tbLyrkbsIDADDaZYhTRwDJuMoc04BmkR-z2D4TvLS; zpw_sek=ZuUG.355636788.a0.-iRXdssXCFTPDmBYJA4mznQ3LPnFcnAV2T1nnJt2Nu07qa6mFzD4knd30h4id0tL4Bf-yrQ_BL3Ae9ElCiWmzm; app.event.zalo.me=616744305790528006"
client = ZaloClient(secret_key_b64, cookie_string)

data = "57i4rgZDfv2WWov6Wf/tnqAhbhEqQBABBMyjYlgSevKXgqrA84aUF2byHLx/cVr5NwTfs1o3O+4VAFV1b3K4ah8ONr/jIJuh5SgZzJHcnrzxAnLgO7nd4uiAlx7hXex3nWCWZ670jz7SQlDKbJ66dsHPtNp8o8DXxuKBcfmcT+tw9D1QX0Frk0PLnn/NyfMtuPR8YoVQZ/AzV8E++pkC2w=="


decode = client.decodeAES(data)
print(decode)
# list_friend = client.getRecommendedFriendsV2()
# print(list_friend)
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


if __name__ == "__main__":
    # 1. Khởi tạo
    
    # 2. Đăng nhập QR (Lấy Cookie id.zalo.me & Session Init)
    user_info = client.wait_for_qr_login()
    
    # if user_info:
    #     # 3. Hoàn tất đăng nhập (Lấy Secret Key cho chat.zalo.me)
    #     # Bước này sẽ sinh zcid, mã hóa params gửi lên server
    #     success = client.finalize_login()
        
    #     if success:
    #         print("Đăng nhập hoàn toàn thành công. Có thể gọi API Chat ngay bây giờ.")
            
    #         # Test thử lấy danh sách bạn bè (cần secret key mới chạy được)
    #         try:
    #             print("Đang lấy danh sách bạn bè...")
    #             # Lưu ý: getUser... cần secret key để decrypt data trả về
    #             # Nếu secret key sai, hàm này sẽ lỗi padding hoặc rác
    #             # friends = zalo.getUserByPhone("09xxxx") 
    #             # print(friends)
    #         except Exception as e:
    #             print(e)
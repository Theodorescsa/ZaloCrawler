from zalo_client import ZaloClient
import json
secret_key_b64 = 'YU9bjfEYcbJPvJozl4s4OQ=='
cookie_string = "ozi=2000.SSZzejyD2DyiZwEqqGn1pJ75lh39JHN1E8Yy_zm36zbwrAxraqyOtpIUfVUMIX7VCj6bz9865zatrQNyD3ar.1; _ga_1J0YGQPT22=GS1.1.1743267239.1.1.1743267278.21.0.0; _gcl_au=1.1.1210773121.1762247361; _fbp=fb.1.1762247361146.837283859710473447; __zi=3000.SSZzejyD2DyiZwEqqGn1pJ75lh39JHN1E8Yy_zm36zbxrAxraayOt3EUhlQGGHEMDP6YkfP75f8rcQUtDG.1; __zi-legacy=3000.SSZzejyD2DyiZwEqqGn1pJ75lh39JHN1E8Yy_zm36zbxrAxraayOt3EUhlQGGHEMDP6YkfP75f8rcQUtDG.1; _ga_NVN38N77J3=GS2.2.s1767670840$o4$g1$t1767670845$j55$l0$h0; _ga_WSPJQT0ZH1=GS2.1.s1767670858$o3$g1$t1767670880$j38$l0$h0; _ga_E63JS7SPBL=GS2.1.s1767670834$o5$g1$t1767670883$j11$l0$h0; _ga_907M127EPP=GS2.1.s1767944044$o7$g1$t1767944083$j21$l0$h0; _gid=GA1.2.1626715681.1768391792; _zlang=vn; app.event.zalo.me=616744305790528006; _ga_3EM8ZPYYN3=GS2.2.s1768397818$o53$g0$t1768397818$j60$l0$h0; zpsid=u5s7.355636788.168.5d3tEfg1nykk5_NUbe77o-_ojVYljF7uhBR_yvkrgf24d61icuPRhFE1nyi; zpw_sek=uZ26.355636788.a0.vPy_gtoh8Vr8FHFeNQiX_GU9H9PUaGEaAP93bnhkU9uUuN6BDiHRaKZO5R8jbXpV0QeLa2UrF5hRgYPX6y8X_G; _ga_YT9TMXZYV9=GS2.1.s1768403726$o15$g0$t1768403726$j60$l0$h0; _ga=GA1.1.759643980.1743071453; _ga_YS1V643LGV=GS2.1.s1768403733$o62$g0$t1768403734$j59$l0$h0; _ga_RYD7END4JE=GS2.2.s1768403734$o60$g1$t1768403734$j60$l0$h0"
client = ZaloClient(secret_key_b64, cookie_string)
data = "yaG1UhO2SDk441T5zEorynHCqavB440lawZx5mJ4bG6ITJgDkJysbZfQAekBgHV4kzgsSHR0wcX0xXH5o3Ft9xnKWRatPFyh0UKOcMqdxV0Y7oiuDbrigSDLT6qsoUYQeZ8Dpw4SS48djEuqwz68jbBKECGAb79waIMsFEvYqliYea6ByZAFXegumThEVmePZ4vG4558wqNFhU7Ru+WlvQ=="
decode = client.decodeAES(data)
print(decode)
# list_friend = client.getRecommendedFriendsV2()
# print(list_friend)
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


# if __name__ == "__main__":
    # 1. Khởi tạo
    
    # 2. Đăng nhập QR (Lấy Cookie id.zalo.me & Session Init)
    # user_info = client.wait_for_qr_login()
    
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
# Glossary — Thuật ngữ dự án

> **Status**: APPROVED
> **Last updated**: 2026-04-17

Thống nhất từ vựng giữa docs, code, và giao tiếp.
Code dùng tiếng Anh, docs/UI có thể song ngữ.

## Entities

| Tiếng Việt    | English (code) | Định nghĩa                                                   | Phase |
| ------------- | -------------- | ------------------------------------------------------------ | ----- |
| Nhà trọ       | Property       | Một toà nhà / dãy trọ. Thuộc về 1 Landlord.                  | MVP   |
| Phòng         | Room           | Đơn vị cho thuê nhỏ nhất, thuộc 1 Property.                  | MVP   |
| Hợp đồng      | Lease          | Thoả thuận thuê giữa Landlord và Tenant cho 1 Room.          | MVP   |
| Dịch vụ       | Service        | Khoản phí ngoài tiền phòng: điện, nước, internet, rác...     | MVP   |
| Chỉ số        | Meter Reading  | Số đọc từ đồng hồ điện/nước tại 1 thời điểm.                 | MVP   |
| Hoá đơn       | Invoice        | Bảng tính tiền hàng tháng cho 1 Room (tiền phòng + dịch vụ). | MVP   |
| Thanh toán    | Payment        | Giao dịch trả tiền cho 1 Invoice.                            | MVP   |
| Tiền cọc      | Deposit        | Tiền đặt cọc khi ký hợp đồng.                                | MVP   |
| Tiền phòng    | Rent           | Giá thuê phòng cố định hàng tháng.                           | MVP   |
| Kỳ thanh toán | Billing Period | Chu kỳ tính tiền, thường là 1 tháng.                         | MVP   |
| Tài sản       | Asset          | Đồ đạc / thiết bị thuộc phòng hoặc nhà.                      | v1.x  |

## Roles

| Tiếng Việt    | English (code) | Định nghĩa                                                        | Phase |
| ------------- | -------------- | ----------------------------------------------------------------- | ----- |
| Chủ nhà       | Landlord       | Người sở hữu/quản lý Property. MVP gộp cả vai trò quản lý.        | MVP   |
| Người thuê    | Tenant         | Người thuê 1 Room. Có thể có nhiều Tenant/Room, 1 người đại diện. | MVP   |
| Người quản lý | Manager        | Người được Landlord uỷ quyền vận hành (tách khỏi Landlord).       | v1.x  |
| Chủ đầu tư    | Investor       | Sở hữu Property, không vận hành, chỉ xem báo cáo.                 | v2.x  |
| Kỹ thuật viên | Technician     | Thợ sửa chữa, nhận task bảo trì từ Landlord/Manager.              | v2.x  |

## Trạng thái (Statuses)

| Entity  | Status        | Nghĩa                                  |
| ------- | ------------- | -------------------------------------- |
| Room    | vacant        | Phòng trống, sẵn sàng cho thuê         |
| Room    | occupied      | Đang có người thuê                     |
| Room    | expiring_soon | Hợp đồng sắp hết hạn (derive từ Lease) |
| Invoice | unpaid        | Chưa thanh toán                        |
| Invoice | partial       | Đã trả một phần                        |
| Invoice | paid          | Đã thanh toán đủ                       |
| Lease   | active        | Đang hiệu lực                          |
| Lease   | expiring_soon | Sắp hết hạn (ví dụ: còn ≤ 30 ngày)     |
| Lease   | expired       | Đã hết hạn                             |
| Lease   | terminated    | Chấm dứt sớm                           |

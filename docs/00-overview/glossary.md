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
| Kỳ thanh toán | Billing Period | Chu kỳ tính tiền, thường là 1 tháng.                                   | MVP   |
| Người ở cùng  | Occupant       | Người ở chung phòng với Tenant, không ký hợp đồng, không có tài khoản. | MVP   |
| Tài sản       | Asset          | Đồ đạc / thiết bị thuộc phòng hoặc nhà.                                | v1.x  |

## Roles

| Tiếng Việt    | English (code) | Định nghĩa                                                        | Phase |
| ------------- | -------------- | ----------------------------------------------------------------- | ----- |
| Chủ nhà       | Landlord       | Người sở hữu/quản lý Property. MVP gộp cả vai trò quản lý.        | MVP   |
| Người thuê    | Tenant         | Người thuê 1 Room. Có thể có nhiều Tenant/Room, 1 người đại diện. | MVP   |
| Người quản lý | Manager        | Người được Landlord uỷ quyền vận hành (tách khỏi Landlord).       | v1.x  |
| Chủ đầu tư    | Investor       | Sở hữu Property, không vận hành, chỉ xem báo cáo.                 | v2.x  |
| Kỹ thuật viên | Technician     | Thợ sửa chữa, nhận task bảo trì từ Landlord/Manager.              | v2.x  |

## Billing Types (Kiểu tính dịch vụ)

| Value        | Vietnamese          | Cách tính                         | Ví dụ                   |
| ------------ | ------------------- | --------------------------------- | ----------------------- |
| `per_meter`  | Theo chỉ số đồng hồ | (số_mới − số_cũ) × đơn_giá        | Điện (kWh), nước (m³)   |
| `per_person` | Theo đầu người      | số_người × đơn_giá                | Rác, giữ xe, thang máy  |
| `fixed`      | Cố định             | đơn_giá (cố định / phòng / tháng) | Internet, vệ sinh chung |

## Service Scope

| Value            | Áp dụng cho                                 |
| ---------------- | ------------------------------------------- |
| `all_rooms`      | Tất cả Room trong Property (default)        |
| `selected_rooms` | Subset Room được chọn (chỉ cho `per_meter`) |

## Trạng thái (Statuses)

**Lưu ý**: Tất cả status dưới đây đều là **computed fields** (trừ
`Lease.terminated` qua `terminated_at`). Không lưu DB, tính khi query.

### Room Status (derive 1-1 từ Lease.status)

| Status          | Nghĩa                                    | Ứng với Lease.status                            |
| --------------- | ---------------------------------------- | ----------------------------------------------- |
| `vacant`        | Phòng trống, sẵn sàng cho thuê           | không có Lease, hoặc `draft`, hoặc `terminated` |
| `occupied`      | Đang có người thuê                       | `active`                                        |
| `expiring_soon` | Hợp đồng sắp hết hạn (còn ≤ 30 ngày)     | `expiring_soon`                                 |
| `lease_expired` | Hợp đồng đã hết hạn, Tenant có thể còn ở | `expired`                                       |

### Lease Status

| Status          | Nghĩa                                                   |
| --------------- | ------------------------------------------------------- |
| `draft`         | Đã tạo nhưng chưa đến start_date                        |
| `active`        | Đang hiệu lực (start_date ≤ today ≤ end_date - 30 days) |
| `expiring_soon` | Sắp hết hạn (còn ≤ 30 ngày đến end_date)                |
| `expired`       | Đã qua end_date, chưa terminated                        |
| `terminated`    | Chấm dứt sớm (có `terminated_at`)                       |

### Tenant Status

| Status      | Nghĩa                                 |
| ----------- | ------------------------------------- |
| `pending`   | Đã tạo record nhưng chưa ký Lease nào |
| `active`    | Đang có Lease không terminated        |
| `moved_out` | Đã archive, tất cả Lease đã kết thúc  |

### Invoice Status

| Status    | Nghĩa            |
| --------- | ---------------- |
| `unpaid`  | Chưa thanh toán  |
| `partial` | Đã trả một phần  |
| `paid`    | Đã thanh toán đủ |

### Deposit Status (field của Lease)

| Status      | Nghĩa                                   |
| ----------- | --------------------------------------- |
| `held`      | Đang giữ cọc (default khi tạo Lease)    |
| `returned`  | Đã trả lại (đủ hoặc 1 phần sau khi trừ) |
| `forfeited` | Mất cọc toàn bộ (Tenant vi phạm)        |
| `deducted`  | Lấy cọc bù nợ                           |

# Vision & Scope

> **Status**: APPROVED
> **Last updated**: 2026-04-17
> **Author**: Claude (as Product Manager)
> **Reviewer**: Bảo (Founder / Domain Expert)
> **Approved by**: Bảo

---

## 1. Problem Statement

Chủ nhà trọ và người quản lý phòng trọ tại Việt Nam (quy mô 5–100 phòng)
đang vận hành bằng tổ hợp Excel + Zalo + sổ tay + giấy tờ.

Workflow hàng tháng lặp lại:

1. Đi đọc số điện/nước từng phòng
2. Mở Excel, nhập số, áp công thức tính tiền
3. Tạo hoá đơn (thường là screenshot bảng tính)
4. Gửi ảnh hoá đơn qua Zalo cho từng người thuê
5. Theo dõi ai đã trả / chưa trả — bằng trí nhớ hoặc ghi chú thủ công
6. Hợp đồng ghi giấy, không biết lúc nào hết hạn cho đến khi nhớ ra

**Hậu quả:**

- Tốn 2–4 giờ/tháng/nhà chỉ riêng việc tính tiền + gửi hoá đơn
- Sai số khi nhập liệu → tranh chấp với người thuê
- Quên nhắc hợp đồng hết hạn → mất quyền kiểm soát
- Không có dữ liệu tổng hợp → không biết nhà nào lãi, nhà nào lỗ
- Khi quản lý hộ nhiều chủ nhà → dữ liệu phân tán, khó báo cáo

**Các giải pháp hiện tại và hạn chế:**

| Giải pháp    | Hạn chế                                                                |
| ------------ | ---------------------------------------------------------------------- |
| Excel + Zalo | Thủ công, phân tán, không scale, dễ sai                                |
| Sổ tay giấy  | Không search, không backup, không chia sẻ                              |
| TingTong     | Setup phức tạp, nhiều role/feature thừa, quá nhiều bước                |
| Các app khác | UI/UX kém, giật lag, feature dư thừa, không tiếp cận được user thực tế |

## 2. Vision Statement

**RMS (Rental Management System)** là nền tảng quản lý phòng trọ
giúp chủ nhà và người quản lý **tự động hoá chu kỳ thu tiền hàng tháng**
và kiểm soát toàn bộ vận hành cho thuê — nhanh hơn, ít bước hơn,
chính xác hơn so với Excel + Zalo.

> **Một câu**: "Từ đọc số điện đến người thuê nhận hoá đơn — trong vài click."

## 3. Target Users (Personas)

### Persona A: Chủ nhà kiêm quản lý (Primary — MVP)

- **Tên đại diện**: Anh Bảo
- **Đặc điểm**: 25–40 tuổi, quản lý 1–10 nhà trọ (5–100 phòng tổng),
  quản lý nhà mình và được chủ nhà khác uỷ quyền quản lý thuê.
  Dùng smartphone là chính, quen Zalo/Excel.
- **Pain points**:
  - Mất 2–4 giờ/tháng/nhà cho chu kỳ tính tiền
  - Sợ tính sai → mất uy tín với người thuê
  - Không nhớ hợp đồng nào sắp hết
  - Dữ liệu nằm rải rác Excel/Zalo, không tổng hợp được
  - Setup app mới quá phức tạp → bỏ ngang
- **Goals**:
  - Gửi hoá đơn chính xác trong vài phút thay vì vài giờ
  - Biết ngay ai chưa trả
  - Được nhắc khi hợp đồng sắp hết
  - Setup nhà/phòng/khách nhanh, ít bước

### Persona B: Người thuê (Secondary — MVP)

- **Tên đại diện**: Minh
- **Đặc điểm**: 20–35 tuổi, thuê phòng trọ, dùng smartphone.
  Không chủ động tìm app — dùng vì chủ nhà yêu cầu.
- **Pain points**:
  - Không rõ hoá đơn tính như thế nào (điện bao nhiêu? nước bao nhiêu?)
  - Không biết hợp đồng hết hạn lúc nào
  - Muốn báo hỏng hóc nhưng phải nhắn Zalo → dễ bị quên
- **Goals**:
  - Xem hoá đơn rõ ràng, minh bạch
  - Biết trạng thái hợp đồng của mình
  - Gửi yêu cầu sửa chữa và biết tiến độ

### Persona C: Chủ đầu tư (ủy quyền cho quản lý) — Post-MVP

- **Đặc điểm**: Sở hữu nhiều nhà nhưng không trực tiếp vận hành.
  Thuê quản lý (như Bảo) chạy hàng ngày.
- **Needs**: Xem báo cáo hoá đơn, doanh thu, tỷ lệ lấp đầy, chi phí bảo trì.
  Không cần thao tác vận hành.

### Persona D: Chủ nhà cho thuê nguyên căn — v2.x

- **Đặc điểm**: Sở hữu nhiều nhà, cho thuê nguyên căn không tách phòng,
  1 người đại diện thuê, không thu dịch vụ (người thuê tự đăng ký với nhà cung cấp).
- **Needs**: Quản lý người thuê đại diện, giá cho thuê nhà, báo cáo doanh thu.
- **Note**: Đây gần như là một product flow riêng (không dùng Room/Service/Invoice).
  Sẽ implement khi core flow phòng trọ đã ổn định, có thể thông qua property type.

### Persona E: Kỹ thuật viên — Post-MVP

- **Đặc điểm**: Thợ điện/nước/điều hoà, nhận việc từ quản lý.
- **Needs**: Nhận task sửa chữa, cập nhật trạng thái, chụp ảnh hoàn thành.

## 4. Core Value Proposition

> **"Ít bước hơn, đúng hơn, nhanh hơn — cho đúng việc cần làm."**

| So với              | RMS khác ở                                                                        |
| ------------------- | --------------------------------------------------------------------------------- |
| Excel + Zalo        | Tự động hoá chu kỳ: nhập số → tính → gửi → theo dõi. Một luồng thay vì 4 công cụ. |
| TingTong / App khác | Setup nhanh hơn (ít bước). Chỉ có feature cần dùng. UI/UX mượt, không lag.        |
| Sổ tay              | Dữ liệu số, search được, backup được, chia sẻ được.                               |

**Chiến lược cạnh tranh**: Do less, but better.
Không thắng về số lượng feature. Thắng về:

- Tốc độ setup (nhà → phòng → khách thuê trong ít bước nhất)
- Tốc độ vận hành hàng tháng (từ đọc số đến gửi hoá đơn)
- Clarity (mọi màn hình rõ mục đích, không thừa)

## 5. Scope

### MVP (v1.0) — IN SCOPE

- [x] Quản lý nhà (CRUD, thông tin cơ bản)
- [x] Quản lý phòng theo nhà (CRUD, trạng thái: trống / đang thuê / sắp hết hạn)
- [x] Quản lý khách thuê theo phòng (CRUD, thông tin cơ bản, số lượng người,
      khách thuê đại diện)
- [x] Cấu hình dịch vụ (điện, nước, internet, rác...) với nhiều kiểu tính
      (theo đồng hồ, theo đầu người, cố định)
- [x] Ghi chỉ số điện/nước hàng tháng (lưu lịch sử, số mới tự động
      thành số cũ cho kỳ tiếp theo)
- [x] Tự động tính hoá đơn tháng (tiền phòng + dịch vụ)
- [x] Xem hoá đơn (landlord view + tenant view)
- [x] Đánh dấu trạng thái thanh toán (đã trả / chưa trả / trả một phần)
- [x] Hợp đồng cơ bản (ngày bắt đầu, ngày kết thúc, tiền cọc, giá phòng)
- [x] Authentication (đăng nhập / đăng ký)
- [x] RBAC: Landlord + Tenant (thiết kế mở để thêm role sau)

**Invoice flow (MVP)**:
Landlord tạo hoá đơn → Tenant thấy hoá đơn trên app →
Landlord nhắc qua Zalo "lên app kiểm tra" → Tenant xem + trả →
Landlord đánh dấu "đã trả".

### v1.x — PLANNED (sau MVP, trước khi mở rộng user)

- [ ] Push notification cho tenant (hoá đơn mới, nhắc trả tiền, hợp đồng sắp hết)
- [ ] Dashboard tổng quan (doanh thu, tỷ lệ phòng trống, nợ)
- [ ] Export hoá đơn (PDF / ảnh)
- [ ] Quản lý tiền cọc (nhận, trừ, hoàn)
- [ ] Quản lý tài sản theo phòng/nhà
- [ ] Role: Manager (quản lý được uỷ quyền, tách khỏi Landlord)

### v2.x — FUTURE

- [ ] Role: Investor / Owner (chủ đầu tư, chỉ xem báo cáo)
- [ ] Role: Technician (nhận/xử lý yêu cầu bảo trì)
- [ ] Property type: cho thuê nguyên căn (Persona D)
- [ ] Yêu cầu bảo trì từ tenant
- [ ] Thanh toán online (tích hợp payment gateway)
- [ ] Multi-language
- [ ] Mobile app (React Native / Flutter)

### NEVER — Không bao giờ làm

- [ ] Marketplace tìm phòng (không phải Trọ Tốt / Phongtro123)
- [ ] Môi giới / hoa hồng giới thiệu (không cần trong core business)
- [ ] Quản lý xây dựng / sửa chữa lớn
- [ ] Kế toán thuế (chỉ cung cấp data, không thay thế kế toán)

## 6. Success Metrics

### Portfolio (3–6 tháng đầu)

- Hoàn thành MVP với full SDLC documentation
- Deploy được lên production (có domain, HTTPS, CI/CD)
- Chính Bảo dùng hàng ngày để quản lý ít nhất 1 nhà trọ thật
- Code quality: test coverage ≥ 70%, clean architecture, API docs

### Production (6–12 tháng)

- Ít nhất 3 chủ nhà ngoài Bảo sử dụng hàng tháng
- Chỉ số gắn bó: user quay lại mỗi tháng (monthly active)
- Giảm thời gian tính hoá đơn từ 2–4 giờ xuống dưới 30 phút / nhà / tháng

## 7. Constraints & Assumptions

**Constraints:**

- **Team**: Solo developer (Bảo) + AI pair (Claude)
- **Budget**: Free-tier infrastructure (sẽ chuyển paid khi có user thật)
- **Timeline**: MVP trong khoảng 8–10 sprint (2–2.5 tháng)
- **Tech**: FastAPI + PostgreSQL + Docker (đã chọn, phù hợp skill hiện tại)
- **Frontend**: TBD — cần quyết định ở Phase 3 (web-first vs mobile-first)

**Assumptions:**

- Chủ nhà trọ quy mô nhỏ–vừa (5–100 phòng) sẵn sàng chuyển từ Excel
  nếu app đủ đơn giản và nhanh hơn
- Người thuê sẽ dùng app nếu chủ nhà yêu cầu và hoá đơn nằm trên đó
- Internet/smartphone đã phổ biến đủ ở cả chủ nhà và người thuê
- Một người có thể vừa là Landlord (nhà mình) vừa là Manager (nhà người khác)
  — implement Manager role ở v1.x

## 8. Risks

| Risk                                             | Impact              | Likelihood          | Mitigation                                                    |
| ------------------------------------------------ | ------------------- | ------------------- | ------------------------------------------------------------- |
| Scope creep — thêm feature liên tục              | Không ship được MVP | Cao                 | Kỷ luật scope: mọi feature ngoài MVP phải qua review          |
| Frontend bottleneck — Bảo chưa chọn/chưa giỏi FE | Delay MVP 1–2 tháng | Trung bình          | Quyết định FE stack sớm ở Phase 3, bắt đầu đơn giản           |
| Chỉ 1 dev — bị burn out                          | Dừng project        | Trung bình          | Sprint 1 tuần + nghỉ Chủ nhật, scope nhỏ mỗi sprint           |
| User không chịu chuyển từ Excel/Zalo             | Không có adoption   | Trung bình          | Dogfood trước, giảm friction onboarding, export Zalo-friendly |
| Data loss / security breach                      | Mất trust vĩnh viễn | Thấp nhưng critical | Backup strategy từ đầu, HTTPS, hash password, validate input  |

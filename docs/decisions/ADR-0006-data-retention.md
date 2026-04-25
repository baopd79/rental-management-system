# ADR-0006: Data Retention Policy

> **Status**: Accepted (MVP scope) — cần review pháp lý trước production
> **Date**: 2026-04-18
> **Deciders**: Bảo (domain expert) + Claude (Senior Architect)

---

## Context

RMS lưu trữ PII (thông tin cá nhân) của Tenant và dữ liệu tài chính
(Invoice, Payment). Hai khung pháp lý VN áp dụng:

- **Nghị định 13/2023/NĐ-CP** (Bảo vệ dữ liệu cá nhân): Yêu cầu
  có căn cứ xử lý dữ liệu, xóa khi hết mục đích, có cơ chế rút
  consent.
- **Luật Kế toán 2015 + Nghị định 174/2016**: Chứng từ kế toán
  (hoá đơn, thanh toán) phải lưu tối thiểu **10 năm**.

**Lưu ý**: Phân tích pháp lý trong ADR này là best-effort của kỹ
sư, không phải tư vấn pháp lý. **Cần review luật sư trước khi
production**.

---

## Decision

### Policy theo loại dữ liệu

#### 1. Tenant PII (họ tên, SĐT, email, CCCD)

| Trạng thái Tenant | Giữ bao lâu | Hành động |
|-------------------|-------------|-----------|
| `active` | Vô thời hạn | Giữ full PII |
| `moved_out` (archived) | 5 năm kể từ `archived_at` | Anonymize sau 5 năm |

**Anonymize** = xóa PII nhưng giữ bản ghi:
```sql
UPDATE tenants SET
    full_name = 'ANONYMIZED',
    phone     = NULL,
    email     = NULL,
    id_number = NULL,    -- CCCD nếu có
    anonymized_at = NOW()
WHERE archived_at < NOW() - INTERVAL '5 years';
```

Row `tenants` vẫn tồn tại để giữ referential integrity với Lease,
Invoice. Chỉ xóa PII.

#### 2. User account (auth)

| Điều kiện | Hành động |
|-----------|-----------|
| Tenant archived + Lease settled | `users.is_active = FALSE` (immediate) |
| Tenant anonymized (5 năm) | Hard delete `users` row |

Khi hard delete `users`: `tenants.user_id` → NULL (nullable FK).

#### 3. Invoice + Payment (chứng từ kế toán)

**Giữ 10 năm, không xóa, không anonymize.**

Lý do: Invoice và Payment là chứng từ tài chính, không phải PII.
Tên Tenant có thể xuất hiện trong Invoice description nhưng đây là
context kế toán, không phải lưu trữ PII độc lập.

#### 4. Audit logs

Giữ **10 năm** — align với Invoice/Payment (xem ADR-0003).

#### 5. Invite tokens + Password reset tokens

Xóa **ngay sau khi dùng** hoặc khi hết TTL:
- Invite token: TTL 7 ngày
- Reset token: TTL 1 giờ

Implement bằng scheduled cleanup job (xem ADR-0002).

#### 6. Refresh tokens

Xóa khi expired (TTL 7 ngày) hoặc khi user logout.
Cleanup job chạy daily.

---

## Schema additions

```sql
-- Thêm vào bảng tenants
anonymized_at  TIMESTAMPTZ  DEFAULT NULL,

-- Thêm vào bảng users (đã có is_active từ RBAC design)
-- Không cần thêm column mới
```

---

## User consent

Theo Nghị định 13/2023, cần có consent khi thu thập dữ liệu.

**MVP implementation**:
- Khi Tenant accept invite → checkbox "Tôi đồng ý cho phép lưu trữ
  thông tin cá nhân để phục vụ quản lý thuê nhà" (required)
- Lưu consent timestamp vào `users.consent_at`

```sql
-- Thêm vào bảng users
consent_at  TIMESTAMPTZ  DEFAULT NULL,
```

**Không implement** cơ chế rút consent trong MVP — phức tạp, cần
tư vấn pháp lý về cách xử lý khi Tenant rút consent nhưng vẫn còn
Lease active. Defer sang v1.x.

---

## Cleanup jobs (phối hợp với ADR-0002)

3 cleanup tasks chạy trong daily cron:

```
Task: cleanup_expired_tokens
  → DELETE FROM invite_tokens WHERE expires_at < NOW()
  → DELETE FROM password_reset_tokens WHERE expires_at < NOW()
  → DELETE FROM refresh_tokens WHERE expires_at < NOW()

Task: anonymize_old_tenants
  → Chạy 1 lần/ngày, nhẹ
  → UPDATE tenants SET full_name='ANONYMIZED', phone=NULL, ...
    WHERE archived_at < NOW() - INTERVAL '5 years'
    AND anonymized_at IS NULL

Task: hard_delete_old_users
  → DELETE FROM users
    WHERE id IN (
      SELECT user_id FROM tenants
      WHERE anonymized_at IS NOT NULL
      AND user_id IS NOT NULL
    )
```

---

## Tenant data export (right to access)

Nghị định 13/2023 yêu cầu cho phép chủ thể dữ liệu xem dữ liệu
của mình.

**MVP**: Tenant xem được Invoice và Payment của mình qua app —
đây là đủ cho MVP.

**Post-MVP**: Implement "Export my data" (JSON/PDF) khi có yêu cầu
thực tế.

---

## Consequences

### Positive
- Có policy rõ ràng ngay từ đầu → không bị "lộ PII" khi scale
- Invoice/Payment giữ 10 năm → đủ cho audit tài chính
- Anonymize thay vì xóa → giữ được lịch sử vận hành

### Negative / Trade-offs
- Anonymize job cần test kỹ — bug ở đây có thể xóa nhầm PII của
  Tenant còn active
- Consent flow thêm friction cho Tenant onboarding
- Chưa có cơ chế rút consent → thiếu so với full GDPR-style compliance

### Neutral
- 5 năm cho PII Tenant là judgment call — Nghị định 13 không quy
  định số năm cụ thể, chỉ nói "hết mục đích xử lý". 5 năm là
  conservative estimate.

---

## ⚠️ Disclaimer

ADR này là thiết kế kỹ thuật dựa trên đọc hiểu pháp luật của kỹ sư.
Không phải tư vấn pháp lý. Trước khi deploy production với dữ liệu
thật, cần review bởi luật sư có chuyên môn về luật dữ liệu VN.

---

## References

- Nghị định 13/2023/NĐ-CP — Bảo vệ dữ liệu cá nhân
- Luật Kế toán 2015, Điều 41 — Thời hạn lưu trữ tài liệu kế toán
- Phase 2 Summary — Section 5: ADR-0006
- Phase 2 Summary — Nhóm 3 (Tenant): data retention draft policy
- ADR-0002: Cron job architecture (cleanup jobs)
- ADR-0003: Audit log (retention 10 năm)

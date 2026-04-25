-- Tạo test database — chạy tự động qua docker-entrypoint-initdb.d khi
-- container khởi tạo lần đầu (data volume trống).
-- Để chạy thủ công sau khi container đã chạy:
--   docker exec -it rental-management-system-postgres psql -U rms -c "CREATE DATABASE rms_test;"
CREATE DATABASE rms_test;

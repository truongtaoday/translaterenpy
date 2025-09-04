import re
import os
import json

# ==============================================================================
# CÁC CHỨC NĂNG GỐC (Chế độ 1 & 2)
# ==============================================================================

def extract_to_translate(original_file_path, output_file_path):
    """
    Chế độ 1: Trích xuất chuỗi trong "" từ file .rpy, bỏ qua old "..."
    Ghi theo định dạng: số_dòng|||chuỗi_gốc
    """
    print(f"--- Bắt đầu trích xuất từ '{original_file_path}' ---")
    try:
        with open(original_file_path, 'r', encoding='utf-8') as f_goc, \
             open(output_file_path, 'w', encoding='utf-8') as f_dich:

            for line_num, line in enumerate(f_goc, 1):
                # Bỏ qua dòng có old "..."
                if re.search(r'\bold\s*"[^"]*"', line):
                    continue

                # Tìm tất cả chuỗi trong ""
                matches = re.findall(r'"([^"]*)"', line)
                for text in matches:
                    if text.strip():  # Chỉ lưu nếu không rỗng
                        f_dich.write(f"{line_num}|||{text}\n")

        print(f"✅ Trích xuất thành công! Đã lưu vào: '{output_file_path}'")
    except FileNotFoundError:
        print(f"❌ Lỗi: Không tìm thấy file '{original_file_path}'.")
    except Exception as e:
        print(f"❌ Lỗi không mong muốn: {e}")


def import_translation(original_file_path, translation_file_path, new_file_path):
    """
    Chế độ 2: Nhập bản dịch từ file đã dịch vào file gốc theo số dòng.
    Thay thế các chuỗi "..." theo thứ tự xuất hiện.
    """
    print(f"--- Bắt đầu nhập bản dịch từ '{translation_file_path}' ---")
    try:
        translations = {}
        with open(translation_file_path, 'r', encoding='utf-8') as f_dich:
            for line in f_dich:
                line = line.strip()
                if not line: continue
                parts = line.split('|||', 1)
                if len(parts) != 2:
                    print(f"⚠️ Bỏ qua dòng không hợp lệ: {line}")
                    continue
                try:
                    line_num = int(parts[0])
                    if line_num not in translations:
                        translations[line_num] = []
                    translations[line_num].append(parts[1])
                except ValueError:
                    print(f"⚠️ Dòng không hợp lệ (số dòng): {line}")

        if not translations:
            print("❌ Lỗi: File dịch rỗng hoặc không hợp lệ.")
            return

        with open(original_file_path, 'r', encoding='utf-8') as f_goc:
            lines = f_goc.readlines()

        # Thay thế từng dòng
        for line_num, trans_list in translations.items():
            idx = line_num - 1
            if idx < 0 or idx >= len(lines):
                print(f"⚠️ Dòng {line_num} nằm ngoài phạm vi file gốc.")
                continue

            line = lines[idx]
            trans_iter = iter(trans_list)

            # Thay thế từng chuỗi "" theo thứ tự
            def replace_quote(match):
                try:
                    return f'"{next(trans_iter)}"'
                except StopIteration:
                    return match.group(0)  # Nếu hết bản dịch, giữ nguyên

            lines[idx] = re.sub(r'"([^"]*)"', replace_quote, line)

        with open(new_file_path, 'w', encoding='utf-8') as f_out:
            f_out.writelines(lines)

        print(f"✅ Nhập bản dịch thành công! File mới: '{new_file_path}'")
    except FileNotFoundError as e:
        print(f"❌ Không tìm thấy file: '{e.filename}'")
    except Exception as e:
        print(f"❌ Lỗi: {e}")


# ==============================================================================
# CÁC CHỨC NĂNG MỚI (Chế độ 3 & 4)
# ==============================================================================

def protect_placeholders(input_file_path, protected_file_path, mapping_file_path):
    """
    Chế độ 3: Thay thế các placeholder bằng mã tạm @@id@@ và lưu bản đồ.
    Hỗ trợ: [abc], {xyz}, <tag>, %(var)s
    """
    print(f"--- Bảo vệ placeholder trong '{input_file_path}' ---")
    # Cập nhật regex: hỗ trợ ký tự Unicode, khoảng trắng
    placeholder_regex = re.compile(
        r'(\[[^\]]*\]|\{[^}]*\}|%\([^)]*\)[a-zA-Z]|%[sdif])'
    )

    placeholders_map = []
    protected_lines = []

    try:
        with open(input_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.rstrip('\n')
                if '|||' not in line:
                    protected_lines.append(line + '\n')
                    continue

                line_num, text = line.split('|||', 1)

                # Tìm và thay thế từng placeholder
                def replace_placeholder(match):
                    ph = match.group(1)
                    ph_id = len(placeholders_map)
                    placeholders_map.append(ph)
                    return f"@@{ph_id}@@"

                protected_text = placeholder_regex.sub(replace_placeholder, text)
                protected_lines.append(f"{line_num}|||{protected_text}\n")

        # Ghi file đã bảo vệ
        with open(protected_file_path, 'w', encoding='utf-8') as f:
            f.writelines(protected_lines)

        # Ghi bản đồ
        with open(mapping_file_path, 'w', encoding='utf-8') as f:
            json.dump(placeholders_map, f, indent=2, ensure_ascii=False)

        print(f"✅ Bảo vệ thành công!")
        print(f"   → File để dịch: '{protected_file_path}'")
        print(f"   → File bản đồ: '{mapping_file_path}'")

    except Exception as e:
        print(f"❌ Lỗi khi bảo vệ placeholder: {e}")


def restore_placeholders(translated_protected_path, final_file_path, mapping_file_path):
    """
    Chế độ 4: Khôi phục các @@id@@ thành placeholder gốc.
    """
    print(f"--- Khôi phục placeholder từ '{translated_protected_path}' ---")
    try:
        with open(mapping_file_path, 'r', encoding='utf-8') as f:
            placeholders_map = json.load(f)

        with open(translated_protected_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Regex tìm mã tạm
        temp_regex = re.compile(r'@@(\d+)@@')

        restored_lines = []
        for line in lines:
            def restore_match(match):
                idx = int(match.group(1))
                if 0 <= idx < len(placeholders_map):
                    return placeholders_map[idx]
                return match.group(0)  # giữ nguyên nếu lỗi

            restored_line = temp_regex.sub(restore_match, line)
            restored_lines.append(restored_line)

        with open(final_file_path, 'w', encoding='utf-8') as f:
            f.writelines(restored_lines)

        print(f"✅ Khôi phục thành công! File cuối: '{final_file_path}'")

    except FileNotFoundError as e:
        print(f"❌ Không tìm thấy file: '{e.filename}'")
    except json.JSONDecodeError:
        print(f"❌ File bản đồ JSON không hợp lệ: '{mapping_file_path}'")
    except Exception as e:
        print(f"❌ Lỗi: {e}")


# ==============================================================================
# GIAO DIỆN CHÍNH
# ==============================================================================

def main():
    print("🎮 CHƯƠNG TRÌNH HỖ TRỢ DỊCH REN'PY 🎮")
    while True:
        print("\n" + "="*50)
        print("CHỌN CHẾ ĐỘ:")
        print("1. Xuất chuỗi gốc để dịch")
        print("2. Nhập bản dịch vào file gốc")
        print("3. Bảo vệ placeholder (trước khi dịch)")
        print("4. Khôi phục placeholder (sau khi dịch)")
        print("0. Thoát")
        choice = input("👉 Chọn (0-4): ").strip()

        if choice == '1':
            print("\n📁 [Chế độ 1] Trích xuất chuỗi từ file .rpy")
            src = input("File gốc (*.rpy): ").strip()
            out = input("File xuất (vd: can_dich.txt): ").strip()
            if src and out:
                extract_to_translate(src, out)

        elif choice == '2':
            print("\n📥 [Chế độ 2] Nhập bản dịch vào file gốc")
            src = input("File gốc (*.rpy): ").strip()
            trans = input("File đã dịch (da_dich.txt): ").strip()
            out = input("File kết quả (game_vn.rpy): ").strip()
            if all([src, trans, out]):
                import_translation(src, trans, out)

        elif choice == '3':
            print("\n🛡️ [Chế độ 3] Bảo vệ placeholder")
            src = input("File cần bảo vệ (can_dich.txt): ").strip()
            out = input("File đã bảo vệ (vd: protected.txt): ").strip()
            map_file = input("File map (mặc định: placeholders_map.json): ").strip()
            if not map_file:
                map_file = "placeholders_map.json"
            if src and out:
                protect_placeholders(src, out, map_file)

        elif choice == '4':
            print("\n🔄 [Chế độ 4] Khôi phục placeholder")
            src = input("File đã dịch (có @@id@@): ").strip()
            out = input("File hoàn chỉnh (da_dich_final.txt): ").strip()
            map_file = input("File map (mặc định: placeholders_map.json): ").strip()
            if not map_file:
                map_file = "placeholders_map.json"
            if src and out:
                restore_placeholders(src, out, map_file)

        elif choice == '0':
            print("👋 Tạm biệt!")
            break
        else:
            print("❌ Lựa chọn không hợp lệ. Vui lòng chọn lại.")


if __name__ == "__main__":
    main()
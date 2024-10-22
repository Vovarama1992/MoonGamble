import os

# Путь к вашей папке
folder_path = r"C:\Users\79136\Desktop\Projects_of_mine\september\MagicWork\magicBack\src\icons"

# Перебираем файлы в папке
for filename in os.listdir(folder_path):
    if filename.endswith(".png"):
        # Разделяем имя файла на части
        parts = filename.split(", lvl")
        if len(parts) == 2:
            new_name = f"lvl{parts[1]}"
            # Полные пути к старому и новому файлам
            old_file = os.path.join(folder_path, filename)
            new_file = os.path.join(folder_path, new_name)
            # Переименовываем файл
            os.rename(old_file, new_file)
            print(f"Переименован: {filename} -> {new_name}")
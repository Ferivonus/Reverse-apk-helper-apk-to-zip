import os
import shutil


def copy_apk_to_zip(folder_path, extensions=('.apk', '.apkm', '.xapk')):
    """
    Creates a copy of .apk, .apkm, or similar files in the specified folder
    and changes the extension of the copies to .zip.
    The original files remain unchanged.

    :param folder_path: The path to the folder containing the APK files.
    :param extensions: The file extensions to look for.
    """

    # Check if the folder path is valid
    if not os.path.isdir(folder_path):
        print("\n" + "=" * 50)
        print(f"ERROR: The specified source folder path was not found or is invalid:")
        print(f"       -> {folder_path}")
        print("Please ensure the path is correct.")
        print("=" * 50 + "\n")
        return

    print(f"\nCreating .zip copies of .apk files in '{folder_path}'...")

    total_copies_created = 0

    try:
        # Iterate over all files and folders in the path
        for file_name in os.listdir(folder_path):
            original_file_path = os.path.join(folder_path, file_name)

            # Check if it's a file and matches the target extensions (case-insensitive)
            if os.path.isfile(original_file_path) and file_name.lower().endswith(extensions):

                # Create the new file name with the .zip extension
                # Splits "app.apk" into ("app", ".apk")
                name_part, old_extension = os.path.splitext(file_name)

                new_file_name = name_part + ".zip"
                new_file_path = os.path.join(folder_path, new_file_name)

                # Check if the .zip file already exists to prevent duplication
                if os.path.exists(new_file_path):
                    print(f" -> Already exists: {new_file_name} (Skipping)")
                    continue

                try:
                    # Copy the original file and save it with the new .zip name
                    # copy2 preserves more metadata (like timestamps) than copy
                    shutil.copy2(original_file_path, new_file_path)
                    print(f" -> Copied: {file_name}  ==>  {new_file_name}")
                    total_copies_created += 1

                except Exception as e:
                    print(f"ERROR: Could not copy or rename '{file_name}': {e}")

        # Report the final results
        if total_copies_created > 0:
            print("\n" + "=" * 70)
            print(f"🎉 Success! 🎉")
            print(f"Total of {total_copies_created} file copies created with the .zip extension.")
            print("Original files remain unchanged in the folder.")
            print("=" * 70 + "\n")
        else:
            print("\n" + "-" * 60)
            print("No new files were processed or all .zip copies already existed.")
            print("-" * 60 + "\n")

    except Exception as e:
        print(f"\nCRITICAL ERROR: An issue occurred during the process: {e}")


# --- User Input Section ---
if __name__ == "__main__":
    print("--- APK to ZIP Copy Creator Tool ---")

    # Get the source folder path
    print("\n[1/1] Please enter the full path to the folder containing the APK files.")
    print("Example Path (Windows): C:/Users/YourName/Desktop/APK_Backups")

    # Get the folder path from the user
    folder_path_input = input("Source Folder Path: ").strip()

    # Run the function
    copy_apk_to_zip(folder_path_input)
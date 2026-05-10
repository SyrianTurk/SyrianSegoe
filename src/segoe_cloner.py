import os
import subprocess
from fontTools.ttLib import TTFont

def clone_original_segoe(backup_dir):
    """
    Clones the original Segoe UI fonts from backup, renames them, 
    and installs them as 'Segoe UI Clone'.
    """
    f_dir = os.path.join(os.environ['WINDIR'], 'Fonts')
    reg_path = r"HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"

    segoe_files = {
        "segoeui.ttf": "Segoe UI Clone",
        "segoeuib.ttf": "Segoe UI Clone Bold",
        "segoeuii.ttf": "Segoe UI Clone Italic",
        "segoeuiz.ttf": "Segoe UI Clone Bold Italic",
        "segoeuil.ttf": "Segoe UI Clone Light",
        "segoeuili.ttf": "Segoe UI Clone Light Italic",
        "segoeuisl.ttf": "Segoe UI Clone Semilight",
        "segoeuisli.ttf": "Segoe UI Clone Semilight Italic",
        "seguisb.ttf": "Segoe UI Clone Semibold",
        "seguisbi.ttf": "Segoe UI Clone Semibold Italic",
        "seguibl.ttf": "Segoe UI Clone Black",
    }

    for src_file, reg_name in segoe_files.items():
        src_path = os.path.join(backup_dir, src_file)
        if not os.path.exists(src_path):
            continue
        try:
            font = TTFont(src_path)
            for record in font['name'].names:
                original_text = record.toUnicode()
                if "Segoe UI" in original_text:
                    new_text = original_text.replace("Segoe UI", "Segoe UI Clone")
                    if record.nameID == 6: # PostScript name
                        new_text = new_text.replace(" ", "")
                    record.string = new_text.encode(record.getEncoding())
            
            output_filename = f"clone_{src_file}"
            target_path = os.path.join(f_dir, output_filename)
            font.save(target_path)
            
            # Register the cloned font in Windows Registry
            subprocess.run(
                ['reg', 'add', reg_path, '/v', f"{reg_name} (TrueType)", '/t', 'REG_SZ', '/d', output_filename, '/f'],
                check=True, creationflags=0x08000000
            )
        except Exception as e:
            print(f"[Cloner] Failed to clone {src_file}: {e}")
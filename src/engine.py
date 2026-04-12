import fontforge
import sys
import os

print("\n[Engine] Starting Stabilized Grid-Sync Builder...")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def get_segoe_metrics(segoe_path):
    """Opens Segoe UI just to steal its native grid (EM) and metrics."""
    f = fontforge.open(segoe_path)
    em = f.em
    ascent = f.ascent
    descent = f.descent
    f.close()
    return em, ascent, descent

def prepare_font(path, target_em, suffix, wipe_latin=False):
    """Safely opens a font, syncs the grid, wipes Latin if needed, and saves it."""
    if path == "NONE" or not os.path.exists(path):
        return None
    
    temp_path = os.path.join(BASE_DIR, f"temp_{suffix}.ttf")
    font = fontforge.open(path)
    
    # 1. Grid Sync (The Requirement)
    if font.em != target_em:
        print(f"     -> Syncing {os.path.basename(path)} grid to {target_em}...")
        font.em = target_em
    
    # 2. Auto-Detect & Map (Wiping existing Latin)
    if wipe_latin:
        print(f"     -> Auto-detecting and clearing Latin slots in {os.path.basename(path)}...")
        font.selection.select(("ranges",), 0x0020, 0x024F)
        font.selection.select(("more", "ranges",), 0x1E00, 0x1EFF)
        font.clear()
        
    font.generate(temp_path)
    font.close()
    return temp_path

def process_weight(latin_path, arabic_path, weight_type, segoe_filename):
    if latin_path == "NONE": return

    print(f"\n[Engine] Processing {weight_type} weight...")
    segoe_path = os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts', segoe_filename)
    
    if not os.path.exists(segoe_path):
        print(f"  -> Error: System {segoe_filename} not found. Skipping...")
        return

    # Phase 0: Get Master Grid
    target_em, s_asc, s_desc = get_segoe_metrics(segoe_path)

    # Phase 1: Prepare Latin (Sync Grid)
    l_temp = prepare_font(latin_path, target_em, f"lat_{weight_type}")

    # Phase 2: Prepare Arabic (Sync Grid + Wipe Latin)
    a_temp = prepare_font(arabic_path, target_em, f"ara_{weight_type}", wipe_latin=True)

    # Phase 3: Prepare Segoe Symbols
    s_temp = os.path.join(BASE_DIR, f"temp_sym_{weight_type}.ttf")
    sf = fontforge.open(segoe_path)
    sf.selection.select(("ranges",), 0x0000, 0x08FF)
    sf.clear()
    for lookup in sf.gsub_lookups: sf.removeLookup(lookup)
    for lookup in sf.gpos_lookups: sf.removeLookup(lookup)
    sf.generate(s_temp)
    sf.close()

    # Phase 4: Final Merge (Assembly Line)
    print("  -> Assembling final font...")
    if a_temp:
        final_font = fontforge.open(a_temp)
        final_font.mergeFonts(l_temp)
    else:
        final_font = fontforge.open(l_temp)
    
    final_font.mergeFonts(s_temp)

    # Phase 5: Metadata & Windows Metrics
    segoe_meta = fontforge.open(segoe_path)
    final_font.fontname = segoe_meta.fontname
    final_font.familyname = segoe_meta.familyname
    final_font.fullname = segoe_meta.fullname
    final_font.sfnt_names = segoe_meta.sfnt_names
    final_font.os2_weight = segoe_meta.os2_weight
    final_font.os2_stylemap = segoe_meta.os2_stylemap
    final_font.macstyle = segoe_meta.macstyle
    
    # Enforce Segoe Metrics for UI Stability
    final_font.ascent = segoe_meta.ascent
    final_font.descent = segoe_meta.descent
    final_font.os2_winascent = segoe_meta.os2_winascent
    final_font.os2_windescent = segoe_meta.os2_windescent
    final_font.hhea_ascent = segoe_meta.hhea_ascent
    final_font.hhea_descent = segoe_meta.hhea_descent
    segoe_meta.close()

    output_name = os.path.join(BASE_DIR, f"{segoe_filename.split('.')[0]}_system_mod.ttf")
    final_font.generate(output_name)
    final_font.close()

    # Cleanup
    for t in [l_temp, a_temp, s_temp]:
        if t and os.path.exists(t): os.remove(t)
    
    print(f"  -> Success! Saved as: {os.path.basename(output_name)}")


# Execution matched pairs
# Mapping the 12 input arguments from app.py to the 6 System Font Weights
weights_map = [
    ("Light", sys.argv[1], sys.argv[7], "segoeuil.ttf"),
    ("Semilight", sys.argv[2], sys.argv[8], "segoeuisl.ttf"),
    ("Regular", sys.argv[3], sys.argv[9], "segoeui.ttf"),
    ("Semibold", sys.argv[4], sys.argv[10], "seguisb.ttf"),
    ("Bold", sys.argv[5], sys.argv[11], "segoeuib.ttf"),
    ("Black", sys.argv[6], sys.argv[12], "seguibl.ttf")
]

for weight_name, lat_path, ara_path, sys_filename in weights_map:
    process_weight(lat_path, ara_path, weight_name, sys_filename)

print("\n[Engine] All system replacement fonts built successfully!")

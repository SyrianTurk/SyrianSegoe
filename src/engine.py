import fontforge
import sys
import os

print("\n[Engine] Starting Stabilized Grid-Sync Builder...")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def get_segoe_metrics(segoe_path):
    """Opens Segoe UI just to get its EM grid."""
    f = fontforge.open(segoe_path)
    em = f.em
    f.close()
    return em

def prepare_font(path, target_em, suffix, wipe_latin=False, strip_ligatures=False, sync_symbols_only=False):
    """Safely opens a font, syncs the grid, wipes Latin if needed, and saves it."""
    if path == "NONE" or not os.path.exists(path):
        return None
    
    temp_path = os.path.join(BASE_DIR, f"temp_{suffix}.ttf")
    font = fontforge.open(path)

    
    # 1. Auto-Detect & Map (Wiping existing Latin)
    if wipe_latin:
        print(f"     -> Auto-detecting and clearing Latin slots in {os.path.basename(path)}...")
        font.selection.select(("ranges",), 0x0020, 0x024F)
        font.selection.select(("more", "ranges",), 0x1E00, 0x1EFF)
        font.clear()

    # 2. Clear Symbols/Punctuation to "sync" them from Segoe (Latin-only mode)
    if sync_symbols_only:
        print(f"     -> Clearing symbols, punctuation, and Arabic in {os.path.basename(path)} to sync from system...")
        font.selection.select(("ranges",), 0x0020, 0x007F) # Basic Latin range
        font.selection.select(("less", "ranges",), 0x0030, 0x0039) # Keep 0-9
        font.selection.select(("less", "ranges",), 0x0041, 0x005A) # Keep A-Z
        font.selection.select(("less", "ranges",), 0x0061, 0x007A) # Keep a-z
        
        # Clear Arabic ranges to ensure joining logic from Segoe UI is used correctly without interference
        font.selection.select(("more", "ranges",), 0x0600, 0x06FF) # Arabic
        font.selection.select(("more", "ranges",), 0x0750, 0x077F) # Arabic Supplement
        font.selection.select(("more", "ranges",), 0x08A0, 0x08FF) # Arabic Extended-A
        font.selection.select(("more", "ranges",), 0xFB50, 0xFDFF) # Presentation Forms A
        font.selection.select(("more", "ranges",), 0xFE70, 0xFEFF) # Presentation Forms B

        font.clear()
        
    # 3. Strip GSUB Lookups
    if strip_ligatures:
        print(f"     -> Stripping ligatures (GSUB) from {os.path.basename(path)}...")
        for lookup in font.gsub_lookups:
            font.removeLookup(lookup)

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

    # Phase 0: Determine Target Grid
    is_latin_only = (arabic_path == "NONE")
    if is_latin_only:
        # Latin only mode: Preserve Latin grid (prevent character distortion)
        # Sync symbols to Latin EM instead
        lf = fontforge.open(latin_path)
        target_em = lf.em
        lf.close()
        print(f"  -> Latin-only mode: Preserved original grid ({target_em} EM)")
    else:
        # Dual mode: Sync everything to Segoe standard grid
        target_em = get_segoe_metrics(segoe_path)
        print(f"  -> Dual mode: Syncing to Segoe grid ({target_em} EM)")

    # Phase 1: Prepare Latin (Sync Grid)
    l_temp = prepare_font(latin_path, target_em, f"lat_{weight_type}", strip_ligatures=True, sync_symbols_only=is_latin_only)

    # Phase 2: Prepare Arabic (Sync Grid + Wipe Latin)
    a_temp = prepare_font(arabic_path, target_em, f"ara_{weight_type}", wipe_latin=True)

    # Phase 3: Prepare Segoe Symbols
    s_temp = os.path.join(BASE_DIR, f"temp_sym_{weight_type}.ttf")
    sf = fontforge.open(segoe_path)

    # Sync Segoe Symbols grid to target_em (Crucial for Latin-only mode)
    if sf.em != target_em:
        sf.em = target_em

    if is_latin_only:
        # Sync symbols/punctuation from Segoe: Wipe ONLY alphanumeric characters
        sf.selection.select(("ranges",), 0x0030, 0x0039) # 0-9
        sf.selection.select(("more", "ranges",), 0x0041, 0x005A) # A-Z
        sf.selection.select(("more", "ranges",), 0x0061, 0x007A) # a-z
        sf.clear()
        # Do NOT remove GSUB/GPOS lookups here. 
        # This preserves Arabic joining logic (init, medi, fina, isol) from Segoe UI.
    else:
        # Dual mode: Wipe basic Latin/Greek/Arabic blocks to prioritize chosen fonts
        sf.selection.select(("ranges",), 0x0000, 0x08FF)
        sf.clear()
        # In dual mode, we strip lookups as they are provided by the chosen Latin/Arabic fonts.
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

import fontforge
import sys
import os
import gc

try:
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
except Exception:
    pass

print("\n[Engine] Starting Stabilized Grid-Sync Builder...")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Glyphs that Windows needs in system fonts (essential for Windows functionality)
ESSENTIAL_GLYPHS = {
    # Basic ASCII & Latin (0x0020 - 0x007E)
    *range(0x0020, 0x007F),
    # Latin Extended-A & B (0x0100 - 0x024F)
    *range(0x0100, 0x0250),
    # Latin Extended Additional (0x1E00 - 0x1EFF)
    *range(0x1E00, 0x1F00),
    # General Punctuation (0x2000 - 0x206F)
    *range(0x2000, 0x2070),
    # Superscripts & Subscripts (0x2070 - 0x209F)
    *range(0x2070, 0x20A0),
    # Currency Symbols (0x20A0 - 0x20CF)
    *range(0x20A0, 0x20D0),
    # Letterlike Symbols (0x2100 - 0x214F)
    *range(0x2100, 0x2150),
    # Number Forms (0x2150 - 0x218F)
    *range(0x2150, 0x2190),
    # Arrows (0x2190 - 0x21FF)
    *range(0x2190, 0x2200),
    # Mathematical Operators (0x2200 - 0x22FF)
    *range(0x2200, 0x2300),
    # Miscellaneous Technical (0x2300 - 0x23FF)
    *range(0x2300, 0x2400),
    # Box Drawing (0x2500 - 0x257F)
    *range(0x2500, 0x2580),
    # Block Elements (0x2580 - 0x259F)
    *range(0x2580, 0x25A0),
    # Geometric Shapes (0x25A0 - 0x25FF)
    *range(0x25A0, 0x2600),
    # Miscellaneous Symbols (0x2600 - 0x26FF)
    *range(0x2600, 0x2700),
    # Dingbats (0x2700 - 0x27BF)
    *range(0x2700, 0x27C0),
    # Greek & Coptic (0x0370 - 0x03FF)
    *range(0x0370, 0x0400),
    # Cyrillic (0x0400 - 0x04FF)
    *range(0x0400, 0x0500),
    # Arabic (0x0600 - 0x06FF)
    *range(0x0600, 0x0700),
    # Arabic Supplement (0x0750 - 0x077F)
    *range(0x0750, 0x0780),
    # Arabic Extended-A (0x08A0 - 0x08FF)
    *range(0x08A0, 0x0900),
    # Arabic Presentation Forms-A (0xFB50 - 0xFDFF)
    *range(0xFB50, 0xFE00),
    # Arabic Presentation Forms-B (0xFE70 - 0xFEFF)
    *range(0xFE70, 0xFF00),
    # Hebrew (0x0590 - 0x05FF)
    *range(0x0590, 0x0600),
    # CJK Symbols & Punctuation (0x3000 - 0x303F)
    *range(0x3000, 0x3040),
    # Hiragana (0x3040 - 0x309F)
    *range(0x3040, 0x30A0),
    # Katakana (0x30A0 - 0x30FF)
    *range(0x30A0, 0x3100),
    # Hangul Compatibility Jamo (0x3130 - 0x318F)
    *range(0x3130, 0x3190),
    # CJK Unified Ideographs (0x4E00 - 0x9FFF, limited subset)
    *range(0x4E00, 0x4FFF),
}

def get_segoe_metrics(segoe_path):
    """Opens Segoe UI just to get its EM grid."""
    f = fontforge.open(segoe_path)
    em = f.em
    f.close()
    return em

def cleanup_unused_glyphs(font, preserve_arabic_joining=False, remove_kern_lookups=True):
    """Remove unused combining marks and problematic glyphs that cause errors."""
    try:
        # First: Optionally remove kern lookups only.
        # Preserve Arabic GPOS entirely when requested.
        try:
            if remove_kern_lookups and not preserve_arabic_joining:
                for lookup in list(font.gpos_lookups):
                    if 'kern' in lookup.lower():
                        try:
                            font.removeLookup(lookup)
                        except:
                            pass
                print(f"     -> Removed only kern GPOS lookups")
            elif remove_kern_lookups and preserve_arabic_joining:
                print(f"     -> Preserved Arabic GPOS and skipped kern cleanup")
            else:
                print(f"     -> Skipped kern lookup cleanup")
        except Exception as e:
            print(f"     -> Warning managing kern lookups: {e}")
        
        if not preserve_arabic_joining:
            try:
                for lookup in list(font.gsub_lookups):
                    try:
                        font.removeLookup(lookup)
                    except:
                        pass
                print(f"     -> Removed GSUB lookups for non-Arabic cleanup")
            except Exception as e:
                print(f"     -> Warning removing GSUB lookups: {e}")
        
        # Second: Remove problematic glyphs by Unicode range
        problematic_glyphs = {
            # Combining Diacritical Marks that often cause spline errors
            'uni0300', 'uni0301', 'uni0302', 'uni0303', 'uni0304', 'uni0305', 'uni0306', 'uni0307',
            'uni0308', 'uni0309', 'uni030A', 'uni030B', 'uni030C', 'uni030D', 'uni030E', 'uni030F',
            'uni0310', 'uni0311', 'uni0312', 'uni0313', 'uni0314', 'uni0315', 'uni0316', 'uni0317',
            'uni0318', 'uni0319', 'uni031A', 'uni031B', 'uni031C', 'uni031D', 'uni031E', 'uni031F',
            'uni0330', 'uni0331', 'uni0332', 'uni0333', 'uni0334', 'uni0335', 'uni0336', 'uni0337',
            # Variation Selectors & Zero-width characters
            'uni180B', 'uni180C', 'uni180D', 'uni180E', 'uni200B',
            'uni2060', 'uni2061', 'uni2062', 'uni2063', 'uni2064', 'uni2065', 'uni2066',
            'uni2067', 'uni2068', 'uni2069', 'uni206A', 'uni206B', 'uni206C', 'uni206D', 'uni206E',
            'uni206F', 'uni3164', 'uniF8FF', 'uni101DC8', 'dotbelowcomb', 'alpha',
        }
        
        if not preserve_arabic_joining:
            problematic_glyphs.update({'uni200C', 'uni200D', 'uni200E', 'uni200F'})
        
        glyphs_to_remove = []
        
        # Use numeric loop instead of direct iteration to avoid hash issues
        glyph_count = len(font.glyphs())
        for i in range(glyph_count):
            try:
                glyph = font.glyphs()[i]
                glyph_name = glyph.name
                
                # Check if it's in problematic list
                if glyph_name in problematic_glyphs:
                    glyphs_to_remove.append(glyph_name)
                # Check if it's a high Unicode codepoint that's not essential
                elif glyph_name.startswith('uni') and len(glyph_name) > 3:
                    try:
                        codepoint = int(glyph_name[3:], 16)
                        # Be aggressive: remove glyphs above 0x1000 that aren't in essential list
                        if codepoint not in ESSENTIAL_GLYPHS and codepoint > 0x1000:
                            glyphs_to_remove.append(glyph_name)
                    except:
                        pass
            except:
                pass
        
        if glyphs_to_remove:
            print(f"     -> Removing {len(glyphs_to_remove)} unused/problematic glyphs...")
            for glyph_name in glyphs_to_remove:
                try:
                    font.removeGlyph(glyph_name)
                except:
                    pass
            
    except Exception as e:
        print(f"     -> Warning during glyph cleanup: {e}")

def cleanup_lookup_tables(font, remove_kern_lookups=True):
    """Remove any remaining kern tables without deleting Arabic positioning lookups."""
    try:
        if not remove_kern_lookups:
            print(f"     -> Skipped lookup cleanup for Arabic-preserved font")
            return
        removed_count = 0
        
        try:
            for lookup in list(font.gpos_lookups):
                if 'kern' in lookup.lower():
                    try:
                        font.removeLookup(lookup)
                        removed_count += 1
                    except:
                        pass
        except:
            pass
        
        if removed_count > 0:
            print(f"     -> Removed {removed_count} kern lookup tables")
            
    except Exception as e:
        print(f"     -> Warning during lookup cleanup: {e}")

def prepare_font(path, target_em, suffix, wipe_latin=False, strip_ligatures=False, sync_symbols_only=False, preserve_arabic_joining=False, remove_kern_lookups=True):
    """Safely opens a font, syncs the grid, wipes Latin if needed, and saves it."""
    if path == "NONE" or not os.path.exists(path):
        return None
    
    temp_path = os.path.join(BASE_DIR, f"temp_{suffix}.ttf")
    font = None
    try:
        font = fontforge.open(path)
        
        # 0. CLEANUP: Remove problematic glyphs early to prevent spline/kern errors
        print(f"     -> Cleaning up problematic glyphs in {os.path.basename(path)}...")
        cleanup_unused_glyphs(font, preserve_arabic_joining, remove_kern_lookups)
        
        # 0b. Additional cleanup of any remaining lookups
        try:
            cleanup_lookup_tables(font, remove_kern_lookups)
        except:
            pass
        
        # 1. Auto-Detect & Map (Wiping existing Latin)
        if wipe_latin:
            try:
                print(f"     -> Auto-detecting and clearing Latin slots in {os.path.basename(path)}...")
                font.selection.select(("ranges",), 0x0020, 0x024F)
                font.selection.select(("more", "ranges",), 0x1E00, 0x1EFF)
                font.clear()
            except Exception as e:
                print(f"     -> Error clearing Latin range: {e}")

        # 2. Clear Symbols/Punctuation to "sync" them from Segoe (Latin-only mode)
        if sync_symbols_only:
            try:
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
            except Exception as e:
                print(f"     -> Error clearing symbols/Arabic: {e}")
            
        # 3. Strip ALL GSUB/GPOS Lookups aggressively (but preserve Arabic features when requested)
        if strip_ligatures:
            try:
                if preserve_arabic_joining:
                    print(f"     -> Preserving Arabic GSUB/GPOS lookups from {os.path.basename(path)}...")
                else:
                    print(f"     -> Stripping ALL lookup tables (GSUB/GPOS) from {os.path.basename(path)}...")
                    for lookup in list(font.gsub_lookups):
                        try:
                            font.removeLookup(lookup)
                        except:
                            pass
                    for lookup in list(font.gpos_lookups):
                        try:
                            font.removeLookup(lookup)
                        except:
                            pass
            except Exception as e:
                print(f"     -> Error stripping lookups: {e}")

        try:
            font.generate(temp_path)
        except Exception as e:
            print(f"     -> Warning during font generation: {e}")
            # Try to save anyway
            try:
                font.save(temp_path)
            except Exception as e2:
                print(f"     -> Error saving font: {e2}")
                return None
                
    except Exception as e:
        print(f"     -> Critical error processing {os.path.basename(path)}: {e}")
        return None
    finally:
        if font:
            try:
                font.close()
            except:
                pass
        gc.collect() # استدعاء يدوي للمنظف لضمان تحرير الموارد
        
    return temp_path

def process_weight(latin_path, arabic_path, weight_type, segoe_filename):
    if latin_path == "NONE": return

    print(f"\n[Engine] Processing {weight_type} weight...")
    segoe_path = os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts', segoe_filename)
    
    if not os.path.exists(segoe_path):
        print(f"  -> Error: System {segoe_filename} not found. Skipping...")
        return

    l_temp = None
    a_temp = None
    s_temp = None
    lf = None
    sf = None
    final_font = None
    segoe_meta = None
    
    try:
        # Phase 0: Determine Target Grid
        is_latin_only = (arabic_path == "NONE")
        if is_latin_only:
            # Latin only mode: Preserve Latin grid (prevent character distortion)
            # Sync symbols to Latin EM instead
            lf = fontforge.open(latin_path)
            target_em = lf.em
            lf.close()
            lf = None
            print(f"  -> Latin-only mode: Preserved original grid ({target_em} EM)")
        else:
            # Dual mode: Sync everything to Segoe standard grid
            target_em = get_segoe_metrics(segoe_path)
            print(f"  -> Dual mode: Syncing to Segoe grid ({target_em} EM)")

        # Phase 1: Prepare Latin (Sync Grid)
        l_temp = prepare_font(latin_path, target_em, f"lat_{weight_type}", strip_ligatures=True, sync_symbols_only=is_latin_only)
        if not l_temp:
            print(f"  -> Error: Failed to prepare Latin font. Skipping {weight_type}...")
            return

        # Phase 2: Prepare Arabic (Sync Grid + Wipe Latin)
        a_temp = prepare_font(arabic_path, target_em, f"ara_{weight_type}", wipe_latin=True, preserve_arabic_joining=True, strip_ligatures=False, remove_kern_lookups=False)
        if not is_latin_only and not a_temp:
            print(f"  -> Error: Failed to prepare Arabic font. Skipping {weight_type}...")
            return

        # Phase 3: Prepare Segoe Symbols
        s_temp = os.path.join(BASE_DIR, f"temp_sym_{weight_type}.ttf")
        try:
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
                try:
                    for lookup in list(sf.gsub_lookups):
                        try:
                            sf.removeLookup(lookup)
                        except:
                            pass
                    for lookup in list(sf.gpos_lookups):
                        try:
                            sf.removeLookup(lookup)
                        except:
                            pass
                except Exception as e:
                    print(f"  -> Warning while removing lookups: {e}")
            
            # Always clean Seoge font without removing Arabic GPOS or kern lookups
            try:
                cleanup_unused_glyphs(sf, preserve_arabic_joining=True, remove_kern_lookups=False)
            except:
                pass

            try:
                sf.generate(s_temp)
            except Exception as e:
                print(f"  -> Warning generating Segoe symbols: {e}")
                try:
                    sf.save(s_temp)
                except Exception as e2:
                    print(f"  -> Error saving Segoe symbols: {e2}")
                    
        except Exception as e:
            print(f"  -> Error processing Segoe symbols: {e}")
            return
        finally:
            if sf:
                try:
                    sf.close()
                except:
                    pass
            sf = None
            gc.collect()

        # Phase 4: Final Merge (Assembly Line)
        try:
            print("  -> Assembling final font...")
            if a_temp and os.path.exists(a_temp):
                final_font = fontforge.open(a_temp)
                final_font.mergeFonts(l_temp)
            else:
                final_font = fontforge.open(l_temp)
            
            if os.path.exists(s_temp):
                final_font.mergeFonts(s_temp)
            
        except Exception as e:
            print(f"  -> Error during font merge: {e}")
            if final_font:
                try:
                    final_font.close()
                except:
                    pass
            return

        # Phase 5: Metadata & Windows Metrics
        try:
            segoe_meta = fontforge.open(segoe_path)
            final_font.fontname = segoe_meta.fontname
            final_font.familyname = segoe_meta.familyname
            final_font.fullname = segoe_meta.fullname
            final_font.sfnt_names = segoe_meta.sfnt_names
            final_font.os2_weight = segoe_meta.os2_weight
            final_font.os2_stylemap = segoe_meta.os2_stylemap
            final_font.macstyle = segoe_meta.macstyle
            segoe_meta.close()
            segoe_meta = None
            
        except Exception as e:
            print(f"  -> Warning updating metadata: {e}")

        output_name = os.path.join(BASE_DIR, f"{segoe_filename.split('.')[0]}_system_mod.ttf")
        
        try:
            final_font.generate(output_name)
        except Exception as e:
            print(f"  -> Error generating final font: {e}")
            try:
                final_font.save(output_name)
            except Exception as e2:
                print(f"  -> Failed to save final font: {e2}")
                return
                
        print(f"  -> Success! Saved as: {os.path.basename(output_name)}")
        
    except Exception as e:
        print(f"  -> Unexpected error processing {weight_type}: {e}")
        
    finally:
        # Cleanup all open fonts and temp files
        for font_obj in [final_font, lf, sf, segoe_meta]:
            if font_obj:
                try:
                    font_obj.close()
                except:
                    pass
        
        for temp_file in [l_temp, a_temp, s_temp]:
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass
        
        gc.collect()


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

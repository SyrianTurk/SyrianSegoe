import os
import shutil
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

def slice_variable_font(var_path, weight_val, out_path):
    """Instantiates a static font from a variable font at a specific weight."""
    font = TTFont(var_path)
    static_font = instantiateVariableFont(font, {"wght": weight_val})
    static_font.save(out_path)

def create_variable_spoof(input_path, output_path):
    """Creates a copy of the font to be used as a placeholder/spoof."""
    try:
        shutil.copy(input_path, output_path)
    except Exception as e:
        print(f"[Slicer] Error copying variable font: {e}")

def resolve_weights(base_path, is_var, reg_path, light_path, semilight_path, semibold_path, bold_path, black_path, lang_prefix):
    """
    Determines the 6 standard weights needed. 
    If variable, it slices them. If static, it maps existing files or defaults to Regular.
    """
    paths = []
    if is_var:
        # Standard Windows weights: Light, Semilight, Reg, Semibold, Bold, Black
        weights = [300, 350, 400, 600, 700, 900] 
        for w in weights:
            out = os.path.join(base_path, f"temp_{lang_prefix}_{w}.ttf")
            slice_variable_font(reg_path, w, out)
            paths.append(out)
    else:
        r = reg_path if reg_path else "NONE"
        lt = light_path if light_path else r
        sl = semilight_path if semilight_path else r
        b = bold_path if bold_path else r
        sb = semibold_path if semibold_path else b
        blk = black_path if black_path else b
        
        paths = [lt, sl, r, sb, b, blk]
    return paths
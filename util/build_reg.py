"""
util/build_reg.py  –  plotviz Windows build helper
Writes dist/plotviz/register_filetypes.reg (UTF-16 LE with BOM, CRLF line
endings) so that double-clicking it registers all plotviz file associations.
Called from create_pkg_win.bat – no arguments needed.
"""
import pathlib

out = pathlib.Path('dist/plotviz/register_filetypes.reg')
out.parent.mkdir(parents=True, exist_ok=True)

CRLF = '\r\n'

lines = [
    'Windows Registry Editor Version 5.00',
    '',
    '; plotviz file-type associations',
    '; Double-click this file (or run as Administrator) to register.',
    '',
    '[HKEY_CLASSES_ROOT\\.pviz]',
    '@="plotviz.Chart"',
    '',
    '[HKEY_CLASSES_ROOT\\plotviz.Chart]',
    '@="plotviz Chart"',
    '',
    '[HKEY_CLASSES_ROOT\\plotviz.Chart\\DefaultIcon]',
    r'@="\"C:\\Program Files\\plotviz\\plotviz.exe\",0"',
    '',
    '[HKEY_CLASSES_ROOT\\plotviz.Chart\\shell\\open\\command]',
    r'@="\"C:\\Program Files\\plotviz\\plotviz.exe\" \"%1\""',
    '',
    '[HKEY_CLASSES_ROOT\\.pvizt]',
    '@="plotviz.Template"',
    '',
    '[HKEY_CLASSES_ROOT\\plotviz.Template]',
    '@="plotviz Template"',
    '',
    '[HKEY_CLASSES_ROOT\\plotviz.Template\\DefaultIcon]',
    r'@="\"C:\\Program Files\\plotviz\\plotviz.exe\",0"',
    '',
    '[HKEY_CLASSES_ROOT\\plotviz.Template\\shell\\open\\command]',
    r'@="\"C:\\Program Files\\plotviz\\plotviz.exe\" \"%1\""',
    '',
    '[HKEY_CLASSES_ROOT\\.pvizc]',
    '@="plotviz.ColorScheme"',
    '',
    '[HKEY_CLASSES_ROOT\\plotviz.ColorScheme]',
    '@="plotviz Color Scheme"',
    '',
    '[HKEY_CLASSES_ROOT\\plotviz.ColorScheme\\DefaultIcon]',
    r'@="\"C:\\Program Files\\plotviz\\plotviz.exe\",0"',
    '',
    '[HKEY_CLASSES_ROOT\\plotviz.ColorScheme\\shell\\open\\command]',
    r'@="\"C:\\Program Files\\plotviz\\plotviz.exe\" \"%1\""',
    '',
    '[HKEY_CLASSES_ROOT\\.pvizp]',
    '@="plotviz.PaletteBundle"',
    '',
    '[HKEY_CLASSES_ROOT\\plotviz.PaletteBundle]',
    '@="plotviz Palette Bundle"',
    '',
    '[HKEY_CLASSES_ROOT\\plotviz.PaletteBundle\\DefaultIcon]',
    r'@="\"C:\\Program Files\\plotviz\\plotviz.exe\",0"',
    '',
    '[HKEY_CLASSES_ROOT\\plotviz.PaletteBundle\\shell\\open\\command]',
    r'@="\"C:\\Program Files\\plotviz\\plotviz.exe\" \"%1\""',
    '',
    '; .pvizx is a standard zip -- registered with the Windows built-in handler',
    '[HKEY_CLASSES_ROOT\\.pvizx]',
    '@="CompressedFolder"',
    '"PerceivedType"="compressed"',
    '',
]

content = CRLF.join(lines)
out.write_text(content, encoding='utf-16')
print(f'  {out} written')

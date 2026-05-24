import bpy

def draw_checkbox_row(box: bpy.types.UILayout, data: bpy.types.AnyType, show_propertys: list[bool], show_property_keys: list[str], label_texts: list[str], data_masks: list[bool], property :str, label_text: str):
    """Convert a list of boolean flags to a column of checkboxes with labels."""
    idx = show_property_keys.index(property)
    show_property = show_propertys[idx]
    box.prop(data, 'show_propertys', index=idx, text=label_text, icon='TRIA_DOWN' if show_property else 'TRIA_RIGHT', emboss=False)
    if show_property:
        _checkbox = box.box()
        for i, _label_text in enumerate(label_texts):
            if not data_masks[i]:
                continue
            row = _checkbox.row()
            row.prop(data, property, index=i, text=_label_text)

def draw_checkbox_column(box: bpy.types.UILayout, data: bpy.types.AnyType, show_propertys: list[bool], show_property_keys: list[str], flags: list[bool], property :str, label_text: str):
    idx = show_property_keys.index(property)
    show_property = show_propertys[idx]
    box.prop(data, 'show_propertys', index=idx, text=label_text, icon='TRIA_DOWN' if show_property else 'TRIA_RIGHT', emboss=False)
    if show_property:
        _checkbox = box.box()
        length=len(flags)
        col = _checkbox.column_flow(columns=length)
        for i in range(length):
            col.prop(data, property, index=i, text='')
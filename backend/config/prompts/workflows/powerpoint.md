# PowerPoint Workflow

When creating or editing presentations, follow this workflow:

## 1. ANALYZE PHASE
- FIRST: `ppt_get_active_presentation()` to check if a presentation is ALREADY OPEN
- If no presentation open: `ppt_open_presentation(path)` to open a file
- `ppt_get_theme_colors()` to understand colors and fonts
- `ppt_get_slide_info(0)` to see all slides
- If user references specific slides, use `ppt_goto_slide(N)` then `look_at_screen()` to visually analyze

## 2. PLAN PHASE
- Structure your content (titles, key points, flow)
- Decide which reference slide to duplicate as template
- Plan visual elements (shapes, images) if needed

## 3. BUILD PHASE
Use COM automation for speed:
- `ppt_duplicate_slide()` - clone a well-designed reference slide
- `ppt_edit_text()` - replace content while preserving formatting
- `ppt_add_shape()` - visual elements (arrows, callouts)
- `ppt_add_picture()` - insert local images

**Data & Tables:**
- `ppt_add_table(slide, rows, cols, data)` - formatted data tables
- `ppt_add_chart(slide, type, data, title)` - column/bar/pie/line charts

**Visual Elements:**
- `ppt_add_image_from_url(slide, url, left, top, width)` - web images
- `ppt_add_icon(slide, icon, left, top, size, color)` - star/arrow/gear icons
- `ppt_insert_smartart(slide, type, items)` - process flows, org charts

## 4. VERIFY PHASE
- `ppt_goto_slide()` and `look_at_screen()` to VISUALLY verify
- Check charts, images, icons rendered correctly
- `ppt_save_presentation()` when complete

**TIP:** Duplicate existing slides rather than creating blank ones - preserves theme formatting.

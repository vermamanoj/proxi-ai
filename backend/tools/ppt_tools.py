"""
PowerPoint Automation Tools for Proxi

Provides programmatic control over PowerPoint presentations while preserving
themes, fonts, and formatting. Uses COM automation on Windows for full fidelity.
"""

import os
import platform
from typing import Optional, List, Dict, Any
from backend.utils.logger import log_system

# Check platform for COM availability
IS_WINDOWS = platform.system() == "Windows"

if IS_WINDOWS:
    try:
        import win32com.client
        import pythoncom
        COM_AVAILABLE = True
    except ImportError:
        COM_AVAILABLE = False
        log_system("win32com not available - PPT tools will use fallback mode", "WARN")
else:
    COM_AVAILABLE = False


def _get_ppt_app():
    """Get or create PowerPoint application instance."""
    if not COM_AVAILABLE:
        return None
    pythoncom.CoInitialize()
    try:
        ppt = win32com.client.Dispatch("PowerPoint.Application")
        ppt.Visible = True  # Make visible for user to see actions
        return ppt
    except Exception as e:
        log_system(f"Failed to start PowerPoint: {e}", "ERR")
        return None


def ppt_get_active_presentation() -> str:
    """
    Gets info about the currently active/open PowerPoint presentation.
    Use this FIRST to check if a presentation is already open before trying to open a file.
    
    Returns:
        Information about the active presentation (name, path, slide count) or error if none open.
    """
    log_system("Checking for active PowerPoint presentation", "PPT")
    
    if not COM_AVAILABLE:
        return "Error: PowerPoint COM automation not available (Windows + pywin32 required)"
    
    try:
        ppt = _get_ppt_app()
        if not ppt:
            return "Error: Could not connect to PowerPoint application"
        
        if ppt.Presentations.Count == 0:
            return "No presentation is currently open in PowerPoint"
        
        presentation = ppt.ActivePresentation
        
        # Get presentation details
        name = presentation.Name
        full_path = presentation.FullName
        slide_count = presentation.Slides.Count
        
        # Get current slide
        current_slide = 1
        try:
            current_slide = ppt.ActiveWindow.View.Slide.SlideIndex
        except:
            pass
        
        # Get slide titles
        slides_info = []
        for i in range(1, min(slide_count + 1, 11)):  # First 10 slides
            title = "Untitled"
            try:
                slide = presentation.Slides(i)
                if slide.Shapes.HasTitle:
                    title = slide.Shapes.Title.TextFrame.TextRange.Text[:40]
            except:
                pass
            slides_info.append(f"  {i}. {title}")
        
        return f"""Active Presentation: {name}
Path: {full_path}
Total Slides: {slide_count}
Current Slide: {current_slide}

Slides:
{chr(10).join(slides_info)}
{"  ..." if slide_count > 10 else ""}

TIP: Use ppt_goto_slide(N) to navigate, ppt_get_slide_info(N) for details, ppt_duplicate_slide(N) to copy."""
    
    except Exception as e:
        log_system(f"Error checking active presentation: {e}", "ERR")
        return f"Error: {e}"


def ppt_open_presentation(file_path: str) -> str:
    """
    Opens a PowerPoint presentation file.
    NOTE: First check ppt_get_active_presentation() - a file may already be open!
    
    Args:
        file_path: Full path to the .pptx file.
    
    Returns:
        Status message indicating success or failure.
    """
    log_system(f"Opening presentation: {file_path}", "PPT")
    
    if not os.path.exists(file_path):
        return f"Error: File not found: {file_path}"
    
    if not COM_AVAILABLE:
        return "Error: PowerPoint COM automation not available (Windows + pywin32 required)"
    
    try:
        ppt = _get_ppt_app()
        if not ppt:
            return "Error: Could not start PowerPoint application"
        
        presentation = ppt.Presentations.Open(file_path)
        slide_count = presentation.Slides.Count
        
        # Get theme info
        theme_name = "Default"
        try:
            if presentation.SlideMaster:
                theme_name = presentation.SlideMaster.Name or "Custom Theme"
        except:
            pass
        
        return f"Opened: {os.path.basename(file_path)} | Slides: {slide_count} | Theme: {theme_name}"
    
    except Exception as e:
        log_system(f"Error opening presentation: {e}", "ERR")
        return f"Error opening file: {e}"


def ppt_get_slide_info(slide_number: int = 0) -> str:
    """
    Gets information about a specific slide or all slides if slide_number is 0.
    
    Args:
        slide_number: 1-indexed slide number, or 0 for all slides summary.
    
    Returns:
        Slide information including title, content count, and layout.
    """
    log_system(f"Getting slide info: slide {slide_number}", "PPT")
    
    if not COM_AVAILABLE:
        return "Error: PowerPoint COM automation not available"
    
    try:
        ppt = _get_ppt_app()
        if not ppt or ppt.Presentations.Count == 0:
            return "Error: No presentation is open"
        
        presentation = ppt.ActivePresentation
        
        if slide_number == 0:
            # Summary of all slides
            info_lines = [f"Presentation: {presentation.Name}", f"Total Slides: {presentation.Slides.Count}", ""]
            for i, slide in enumerate(presentation.Slides, 1):
                title = "Untitled"
                try:
                    if slide.Shapes.HasTitle:
                        title = slide.Shapes.Title.TextFrame.TextRange.Text[:50]
                except:
                    pass
                info_lines.append(f"  Slide {i}: {title}")
            return "\n".join(info_lines)
        
        else:
            # Specific slide info
            if slide_number > presentation.Slides.Count:
                return f"Error: Slide {slide_number} does not exist (max: {presentation.Slides.Count})"
            
            slide = presentation.Slides(slide_number)
            
            title = "Untitled"
            try:
                if slide.Shapes.HasTitle:
                    title = slide.Shapes.Title.TextFrame.TextRange.Text
            except:
                pass
            
            shape_count = slide.Shapes.Count
            text_shapes = []
            
            for shape in slide.Shapes:
                try:
                    if shape.HasTextFrame and shape.TextFrame.HasText:
                        text_preview = shape.TextFrame.TextRange.Text[:100]
                        text_shapes.append(f"  - {shape.Name}: \"{text_preview}...\"")
                except:
                    pass
            
            info = [
                f"Slide {slide_number}: {title}",
                f"Layout: {slide.Layout}",
                f"Shape Count: {shape_count}",
                "Text Content:"
            ] + text_shapes[:5]  # Limit to 5 shapes
            
            return "\n".join(info)
    
    except Exception as e:
        log_system(f"Error getting slide info: {e}", "ERR")
        return f"Error: {e}"


def ppt_edit_text(slide_number: int, shape_name: str, new_text: str) -> str:
    """
    Edits text in a specific shape on a slide, preserving formatting.
    
    Args:
        slide_number: 1-indexed slide number.
        shape_name: Name of the shape (e.g., "Title 1", "Content Placeholder 2").
        new_text: The new text content to set.
    
    Returns:
        Status message indicating success or failure.
    """
    log_system(f"Editing text on slide {slide_number}, shape '{shape_name}'", "PPT")
    
    if not COM_AVAILABLE:
        return "Error: PowerPoint COM automation not available"
    
    try:
        ppt = _get_ppt_app()
        if not ppt or ppt.Presentations.Count == 0:
            return "Error: No presentation is open"
        
        presentation = ppt.ActivePresentation
        
        if slide_number > presentation.Slides.Count:
            return f"Error: Slide {slide_number} does not exist"
        
        slide = presentation.Slides(slide_number)
        
        # Find shape by name (case-insensitive partial match)
        target_shape = None
        for shape in slide.Shapes:
            if shape_name.lower() in shape.Name.lower():
                target_shape = shape
                break
        
        if not target_shape:
            available = [s.Name for s in slide.Shapes]
            return f"Error: Shape '{shape_name}' not found. Available: {available}"
        
        if not target_shape.HasTextFrame:
            return f"Error: Shape '{shape_name}' does not contain text"
        
        # Preserve formatting by only changing text, not style
        target_shape.TextFrame.TextRange.Text = new_text
        
        return f"Updated '{shape_name}' on slide {slide_number}"
    
    except Exception as e:
        log_system(f"Error editing text: {e}", "ERR")
        return f"Error: {e}"


def ppt_add_slide(after_slide: int = 0, layout: str = "title_content") -> str:
    """
    Adds a new slide to the presentation, inheriting the theme.
    
    Args:
        after_slide: Insert after this slide number (0 = at end).
        layout: Layout type - "title", "title_content", "blank", "two_content".
    
    Returns:
        Status message with the new slide number.
    """
    log_system(f"Adding slide after {after_slide} with layout '{layout}'", "PPT")
    
    if not COM_AVAILABLE:
        return "Error: PowerPoint COM automation not available"
    
    # Layout mapping (ppLayoutType constants)
    LAYOUTS = {
        "title": 1,           # ppLayoutTitle
        "title_content": 2,   # ppLayoutText (Title + Content)
        "blank": 12,          # ppLayoutBlank
        "two_content": 3,     # ppLayoutTwoColumnText
        "section": 11,        # ppLayoutSectionHeader
        "comparison": 4,      # ppLayoutComparison
    }
    
    layout_id = LAYOUTS.get(layout.lower(), 2)
    
    try:
        ppt = _get_ppt_app()
        if not ppt or ppt.Presentations.Count == 0:
            return "Error: No presentation is open"
        
        presentation = ppt.ActivePresentation
        
        insert_pos = after_slide if after_slide > 0 else presentation.Slides.Count
        
        # Add slide with layout from slide master (preserves theme)
        new_slide = presentation.Slides.Add(insert_pos + 1, layout_id)
        
        return f"Added slide {new_slide.SlideIndex} with '{layout}' layout"
    
    except Exception as e:
        log_system(f"Error adding slide: {e}", "ERR")
        return f"Error: {e}"


def ppt_duplicate_slide(slide_number: int) -> str:
    """
    Duplicates an existing slide, preserving all formatting and content.
    
    Args:
        slide_number: The slide number to duplicate.
    
    Returns:
        Status message with the new slide number.
    """
    log_system(f"Duplicating slide {slide_number}", "PPT")
    
    if not COM_AVAILABLE:
        return "Error: PowerPoint COM automation not available"
    
    try:
        ppt = _get_ppt_app()
        if not ppt or ppt.Presentations.Count == 0:
            return "Error: No presentation is open"
        
        presentation = ppt.ActivePresentation
        
        if slide_number > presentation.Slides.Count:
            return f"Error: Slide {slide_number} does not exist"
        
        slide = presentation.Slides(slide_number)
        new_slide = slide.Duplicate()
        
        return f"Duplicated slide {slide_number} → new slide {new_slide.SlideIndex}"
    
    except Exception as e:
        log_system(f"Error duplicating slide: {e}", "ERR")
        return f"Error: {e}"


def ppt_delete_slide(slide_number: int) -> str:
    """
    Deletes a slide from the presentation.
    
    Args:
        slide_number: The slide number to delete.
    
    Returns:
        Status message indicating success or failure.
    """
    log_system(f"Deleting slide {slide_number}", "PPT")
    
    if not COM_AVAILABLE:
        return "Error: PowerPoint COM automation not available"
    
    try:
        ppt = _get_ppt_app()
        if not ppt or ppt.Presentations.Count == 0:
            return "Error: No presentation is open"
        
        presentation = ppt.ActivePresentation
        
        if slide_number > presentation.Slides.Count:
            return f"Error: Slide {slide_number} does not exist"
        
        presentation.Slides(slide_number).Delete()
        
        return f"Deleted slide {slide_number}. Remaining: {presentation.Slides.Count} slides"
    
    except Exception as e:
        log_system(f"Error deleting slide: {e}", "ERR")
        return f"Error: {e}"


def ppt_save_presentation(save_as_path: Optional[str] = None) -> str:
    """
    Saves the current presentation. Optionally saves to a new file.
    
    Args:
        save_as_path: Optional new file path. If None, saves to original location.
    
    Returns:
        Status message with saved file path.
    """
    log_system(f"Saving presentation: {save_as_path or 'original location'}", "PPT")
    
    if not COM_AVAILABLE:
        return "Error: PowerPoint COM automation not available"
    
    try:
        ppt = _get_ppt_app()
        if not ppt or ppt.Presentations.Count == 0:
            return "Error: No presentation is open"
        
        presentation = ppt.ActivePresentation
        
        if save_as_path:
            presentation.SaveAs(save_as_path)
            return f"Saved as: {save_as_path}"
        else:
            presentation.Save()
            return f"Saved: {presentation.FullName}"
    
    except Exception as e:
        log_system(f"Error saving presentation: {e}", "ERR")
        return f"Error: {e}"


def ppt_goto_slide(slide_number: int) -> str:
    """
    Navigates to a specific slide in the presentation.
    
    Args:
        slide_number: The slide number to navigate to.
    
    Returns:
        Status message indicating current slide.
    """
    log_system(f"Navigating to slide {slide_number}", "PPT")
    
    if not COM_AVAILABLE:
        return "Error: PowerPoint COM automation not available"
    
    try:
        ppt = _get_ppt_app()
        if not ppt or ppt.Presentations.Count == 0:
            return "Error: No presentation is open"
        
        presentation = ppt.ActivePresentation
        
        if slide_number > presentation.Slides.Count:
            return f"Error: Slide {slide_number} does not exist (max: {presentation.Slides.Count})"
        
        # Select the slide
        presentation.Slides(slide_number).Select()
        
        # Get slide title for confirmation
        title = "Untitled"
        try:
            slide = presentation.Slides(slide_number)
            if slide.Shapes.HasTitle:
                title = slide.Shapes.Title.TextFrame.TextRange.Text[:50]
        except:
            pass
        
        return f"Now on slide {slide_number}: {title}"
    
    except Exception as e:
        log_system(f"Error navigating: {e}", "ERR")
        return f"Error: {e}"


def ppt_add_picture(slide_number: int, image_path: str, left: int = 100, top: int = 100, width: int = 400) -> str:
    """
    Adds a picture to a slide at the specified position.
    
    Args:
        slide_number: 1-indexed slide number.
        image_path: Full path to the image file (jpg, png, etc.).
        left: X position in points (1 inch = 72 points).
        top: Y position in points.
        width: Width in points (height auto-scales).
    
    Returns:
        Status message indicating success or failure.
    """
    log_system(f"Adding picture to slide {slide_number}: {image_path}", "PPT")
    
    if not COM_AVAILABLE:
        return "Error: PowerPoint COM automation not available"
    
    if not os.path.exists(image_path):
        return f"Error: Image file not found: {image_path}"
    
    try:
        ppt = _get_ppt_app()
        if not ppt or ppt.Presentations.Count == 0:
            return "Error: No presentation is open"
        
        presentation = ppt.ActivePresentation
        
        if slide_number > presentation.Slides.Count:
            return f"Error: Slide {slide_number} does not exist"
        
        slide = presentation.Slides(slide_number)
        
        # AddPicture(FileName, LinkToFile, SaveWithDocument, Left, Top, Width, Height)
        # Height=-1 means auto-scale maintaining aspect ratio
        shape = slide.Shapes.AddPicture(
            image_path,
            LinkToFile=False,
            SaveWithDocument=True,
            Left=left,
            Top=top,
            Width=width,
            Height=-1
        )
        
        return f"Added picture '{os.path.basename(image_path)}' to slide {slide_number} (shape: {shape.Name})"
    
    except Exception as e:
        log_system(f"Error adding picture: {e}", "ERR")
        return f"Error: {e}"


def ppt_add_shape(slide_number: int, shape_type: str, left: int, top: int, width: int, height: int, text: str = "") -> str:
    """
    Adds a shape to a slide with optional text.
    
    Args:
        slide_number: 1-indexed slide number.
        shape_type: Type of shape - "rectangle", "oval", "rounded_rect", "arrow_right", "callout".
        left: X position in points.
        top: Y position in points.
        width: Width in points.
        height: Height in points.
        text: Optional text to add inside the shape.
    
    Returns:
        Status message with shape name.
    """
    log_system(f"Adding {shape_type} shape to slide {slide_number}", "PPT")
    
    if not COM_AVAILABLE:
        return "Error: PowerPoint COM automation not available"
    
    # MsoAutoShapeType constants
    SHAPE_TYPES = {
        "rectangle": 1,        # msoShapeRectangle
        "oval": 9,             # msoShapeOval
        "rounded_rect": 5,     # msoShapeRoundedRectangle
        "arrow_right": 33,     # msoShapeRightArrow
        "arrow_left": 34,      # msoShapeLeftArrow
        "arrow_up": 35,        # msoShapeUpArrow
        "arrow_down": 36,      # msoShapeDownArrow
        "callout": 105,        # msoShapeRoundedRectangularCallout
        "star": 12,            # msoShape5pointStar
        "diamond": 4,          # msoShapeDiamond
    }
    
    shape_id = SHAPE_TYPES.get(shape_type.lower(), 1)
    
    try:
        ppt = _get_ppt_app()
        if not ppt or ppt.Presentations.Count == 0:
            return "Error: No presentation is open"
        
        presentation = ppt.ActivePresentation
        
        if slide_number > presentation.Slides.Count:
            return f"Error: Slide {slide_number} does not exist"
        
        slide = presentation.Slides(slide_number)
        shape = slide.Shapes.AddShape(shape_id, left, top, width, height)
        
        if text:
            shape.TextFrame.TextRange.Text = text
        
        return f"Added {shape_type} to slide {slide_number} (shape: {shape.Name})"
    
    except Exception as e:
        log_system(f"Error adding shape: {e}", "ERR")
        return f"Error: {e}"


def ppt_move_shape(slide_number: int, shape_name: str, left: int, top: int) -> str:
    """
    Moves a shape to a new position on the slide.
    
    Args:
        slide_number: 1-indexed slide number.
        shape_name: Name of the shape to move.
        left: New X position in points.
        top: New Y position in points.
    
    Returns:
        Status message.
    """
    log_system(f"Moving shape '{shape_name}' on slide {slide_number}", "PPT")
    
    if not COM_AVAILABLE:
        return "Error: PowerPoint COM automation not available"
    
    try:
        ppt = _get_ppt_app()
        if not ppt or ppt.Presentations.Count == 0:
            return "Error: No presentation is open"
        
        presentation = ppt.ActivePresentation
        slide = presentation.Slides(slide_number)
        
        # Find shape
        target_shape = None
        for shape in slide.Shapes:
            if shape_name.lower() in shape.Name.lower():
                target_shape = shape
                break
        
        if not target_shape:
            available = [s.Name for s in slide.Shapes]
            return f"Error: Shape '{shape_name}' not found. Available: {available}"
        
        old_pos = (target_shape.Left, target_shape.Top)
        target_shape.Left = left
        target_shape.Top = top
        
        return f"Moved '{shape_name}' from ({old_pos[0]:.0f}, {old_pos[1]:.0f}) to ({left}, {top})"
    
    except Exception as e:
        log_system(f"Error moving shape: {e}", "ERR")
        return f"Error: {e}"


def ppt_resize_shape(slide_number: int, shape_name: str, width: int, height: int) -> str:
    """
    Resizes a shape on the slide.
    
    Args:
        slide_number: 1-indexed slide number.
        shape_name: Name of the shape to resize.
        width: New width in points.
        height: New height in points.
    
    Returns:
        Status message.
    """
    log_system(f"Resizing shape '{shape_name}' on slide {slide_number}", "PPT")
    
    if not COM_AVAILABLE:
        return "Error: PowerPoint COM automation not available"
    
    try:
        ppt = _get_ppt_app()
        if not ppt or ppt.Presentations.Count == 0:
            return "Error: No presentation is open"
        
        presentation = ppt.ActivePresentation
        slide = presentation.Slides(slide_number)
        
        target_shape = None
        for shape in slide.Shapes:
            if shape_name.lower() in shape.Name.lower():
                target_shape = shape
                break
        
        if not target_shape:
            return f"Error: Shape '{shape_name}' not found"
        
        old_size = (target_shape.Width, target_shape.Height)
        target_shape.Width = width
        target_shape.Height = height
        
        return f"Resized '{shape_name}' from ({old_size[0]:.0f}x{old_size[1]:.0f}) to ({width}x{height})"
    
    except Exception as e:
        log_system(f"Error resizing shape: {e}", "ERR")
        return f"Error: {e}"


def ppt_format_text(slide_number: int, shape_name: str, bold: bool = None, italic: bool = None, 
                    font_size: int = None, font_color: str = None) -> str:
    """
    Formats text in a shape (bold, italic, size, color).
    
    Args:
        slide_number: 1-indexed slide number.
        shape_name: Name of the shape containing text.
        bold: Set text bold (True/False).
        italic: Set text italic (True/False).
        font_size: Font size in points.
        font_color: Color as hex string (e.g., "FF0000" for red).
    
    Returns:
        Status message.
    """
    log_system(f"Formatting text in '{shape_name}' on slide {slide_number}", "PPT")
    
    if not COM_AVAILABLE:
        return "Error: PowerPoint COM automation not available"
    
    try:
        ppt = _get_ppt_app()
        if not ppt or ppt.Presentations.Count == 0:
            return "Error: No presentation is open"
        
        presentation = ppt.ActivePresentation
        slide = presentation.Slides(slide_number)
        
        target_shape = None
        for shape in slide.Shapes:
            if shape_name.lower() in shape.Name.lower():
                target_shape = shape
                break
        
        if not target_shape:
            return f"Error: Shape '{shape_name}' not found"
        
        if not target_shape.HasTextFrame:
            return f"Error: Shape '{shape_name}' has no text"
        
        text_range = target_shape.TextFrame.TextRange
        font = text_range.Font
        changes = []
        
        if bold is not None:
            font.Bold = bold
            changes.append(f"bold={bold}")
        
        if italic is not None:
            font.Italic = italic
            changes.append(f"italic={italic}")
        
        if font_size is not None:
            font.Size = font_size
            changes.append(f"size={font_size}")
        
        if font_color is not None:
            # Convert hex to RGB integer
            rgb = int(font_color, 16)
            font.Color.RGB = rgb
            changes.append(f"color=#{font_color}")
        
        return f"Formatted '{shape_name}': {', '.join(changes)}"
    
    except Exception as e:
        log_system(f"Error formatting text: {e}", "ERR")
        return f"Error: {e}"


def ppt_get_theme_colors(slide_number: int = 1) -> str:
    """
    Extracts theme colors from the presentation for consistency.
    
    Args:
        slide_number: Slide to analyze (default 1).
    
    Returns:
        Theme color information.
    """
    log_system(f"Getting theme colors from slide {slide_number}", "PPT")
    
    if not COM_AVAILABLE:
        return "Error: PowerPoint COM automation not available"
    
    try:
        ppt = _get_ppt_app()
        if not ppt or ppt.Presentations.Count == 0:
            return "Error: No presentation is open"
        
        presentation = ppt.ActivePresentation
        
        # Get theme colors
        theme_info = []
        try:
            theme = presentation.SlideMaster.Theme
            scheme = theme.ThemeColorScheme
            
            color_names = [
                "Background1", "Text1", "Background2", "Text2",
                "Accent1", "Accent2", "Accent3", "Accent4", "Accent5", "Accent6"
            ]
            
            for i, name in enumerate(color_names, 1):
                try:
                    color = scheme.Colors(i)
                    rgb = color.RGB
                    # Convert to hex
                    hex_color = f"{rgb & 0xFF:02X}{(rgb >> 8) & 0xFF:02X}{(rgb >> 16) & 0xFF:02X}"
                    theme_info.append(f"  {name}: #{hex_color}")
                except:
                    pass
        except:
            theme_info.append("  Could not read theme scheme")
        
        # Get font info from master
        font_info = []
        try:
            master = presentation.SlideMaster
            title_font = master.TextStyles(1).Levels(1).Font.Name  # Title
            body_font = master.TextStyles(2).Levels(1).Font.Name   # Body
            font_info.append(f"  Title Font: {title_font}")
            font_info.append(f"  Body Font: {body_font}")
        except:
            font_info.append("  Could not read fonts")
        
        return "Theme Colors:\n" + "\n".join(theme_info) + "\n\nFonts:\n" + "\n".join(font_info)
    
    except Exception as e:
        log_system(f"Error getting theme: {e}", "ERR")
        return f"Error: {e}"


def ppt_add_table(slide_number: int, rows: int, cols: int, data: List[List[str]], 
                  left: int = 50, top: int = 150, width: int = 600) -> str:
    """
    Adds a professional table to a slide with data. Tables auto-inherit theme styling.
    Perfect for business cases, comparisons, and data summaries.
    
    Args:
        slide_number: 1-indexed slide number.
        rows: Number of rows (including header).
        cols: Number of columns.
        data: 2D list of cell values, e.g., [["Header1", "Header2"], ["Value1", "Value2"]].
        left: X position in points (default 50).
        top: Y position in points (default 150).
        width: Table width in points (default 600).
    
    Returns:
        Status message with table info.
    """
    log_system(f"Adding {rows}x{cols} table to slide {slide_number}", "PPT")
    
    if not COM_AVAILABLE:
        return "Error: PowerPoint COM automation not available"
    
    try:
        ppt = _get_ppt_app()
        if not ppt or ppt.Presentations.Count == 0:
            return "Error: No presentation is open"
        
        presentation = ppt.ActivePresentation
        
        if slide_number > presentation.Slides.Count:
            return f"Error: Slide {slide_number} does not exist"
        
        slide = presentation.Slides(slide_number)
        
        # Calculate row height based on content
        row_height = 30  # Default row height
        table_height = rows * row_height
        
        # Add table shape
        table_shape = slide.Shapes.AddTable(rows, cols, left, top, width, table_height)
        table = table_shape.Table
        
        # Populate cells with data
        for row_idx, row_data in enumerate(data):
            for col_idx, cell_value in enumerate(row_data):
                if row_idx < rows and col_idx < cols:
                    table.Cell(row_idx + 1, col_idx + 1).Shape.TextFrame.TextRange.Text = str(cell_value)
        
        # Style header row (first row bold)
        for col_idx in range(1, cols + 1):
            try:
                table.Cell(1, col_idx).Shape.TextFrame.TextRange.Font.Bold = True
            except:
                pass
        
        return f"Added {rows}x{cols} table to slide {slide_number} (shape: {table_shape.Name})"
    
    except Exception as e:
        log_system(f"Error adding table: {e}", "ERR")
        return f"Error: {e}"


def ppt_set_shape_style(slide_number: int, shape_name: str, fill_color: str = None, 
                        line_color: str = None, line_weight: float = None,
                        transparency: float = None) -> str:
    """
    Styles a shape with fill color, border, and transparency. Use theme colors for brand consistency.
    
    Args:
        slide_number: 1-indexed slide number.
        shape_name: Name of the shape to style.
        fill_color: Fill color as hex (e.g., "0066CC" for blue). Use "none" for no fill.
        line_color: Border color as hex. Use "none" for no border.
        line_weight: Border thickness in points (e.g., 1.5).
        transparency: Fill transparency 0-100 (0=opaque, 100=invisible).
    
    Returns:
        Status message.
    """
    log_system(f"Styling shape '{shape_name}' on slide {slide_number}", "PPT")
    
    if not COM_AVAILABLE:
        return "Error: PowerPoint COM automation not available"
    
    try:
        ppt = _get_ppt_app()
        if not ppt or ppt.Presentations.Count == 0:
            return "Error: No presentation is open"
        
        presentation = ppt.ActivePresentation
        slide = presentation.Slides(slide_number)
        
        # Find shape
        target_shape = None
        for shape in slide.Shapes:
            if shape_name.lower() in shape.Name.lower():
                target_shape = shape
                break
        
        if not target_shape:
            available = [s.Name for s in slide.Shapes]
            return f"Error: Shape '{shape_name}' not found. Available: {available}"
        
        changes = []
        
        # Set fill color
        if fill_color:
            if fill_color.lower() == "none":
                target_shape.Fill.Visible = False
                changes.append("fill=none")
            else:
                target_shape.Fill.Visible = True
                target_shape.Fill.Solid()
                rgb = int(fill_color, 16)
                # Convert BGR to RGB for PowerPoint
                r = (rgb >> 16) & 0xFF
                g = (rgb >> 8) & 0xFF
                b = rgb & 0xFF
                target_shape.Fill.ForeColor.RGB = r + (g << 8) + (b << 16)
                changes.append(f"fill=#{fill_color}")
        
        # Set line/border
        if line_color:
            if line_color.lower() == "none":
                target_shape.Line.Visible = False
                changes.append("line=none")
            else:
                target_shape.Line.Visible = True
                rgb = int(line_color, 16)
                r = (rgb >> 16) & 0xFF
                g = (rgb >> 8) & 0xFF
                b = rgb & 0xFF
                target_shape.Line.ForeColor.RGB = r + (g << 8) + (b << 16)
                changes.append(f"line=#{line_color}")
        
        if line_weight is not None:
            target_shape.Line.Weight = line_weight
            changes.append(f"weight={line_weight}pt")
        
        # Set transparency
        if transparency is not None:
            target_shape.Fill.Transparency = transparency / 100.0
            changes.append(f"transparency={transparency}%")
        
        return f"Styled '{shape_name}': {', '.join(changes)}"
    
    except Exception as e:
        log_system(f"Error styling shape: {e}", "ERR")
        return f"Error: {e}"


def ppt_add_textbox(slide_number: int, text: str, left: int, top: int, 
                    width: int = 300, height: int = 50, 
                    font_size: int = None, font_color: str = None,
                    bold: bool = False, align: str = "left") -> str:
    """
    Adds a text box to a slide with custom positioning and formatting.
    Great for labels, callouts, and annotations.
    
    Args:
        slide_number: 1-indexed slide number.
        text: Text content for the textbox.
        left: X position in points.
        top: Y position in points.
        width: Width in points (default 300).
        height: Height in points (default 50).
        font_size: Optional font size in points.
        font_color: Optional hex color (e.g., "333333").
        bold: Make text bold (default False).
        align: Text alignment - "left", "center", "right" (default "left").
    
    Returns:
        Status message with textbox info.
    """
    log_system(f"Adding textbox to slide {slide_number}", "PPT")
    
    if not COM_AVAILABLE:
        return "Error: PowerPoint COM automation not available"
    
    # Alignment constants
    ALIGN = {"left": 1, "center": 2, "right": 3}
    
    try:
        ppt = _get_ppt_app()
        if not ppt or ppt.Presentations.Count == 0:
            return "Error: No presentation is open"
        
        presentation = ppt.ActivePresentation
        
        if slide_number > presentation.Slides.Count:
            return f"Error: Slide {slide_number} does not exist"
        
        slide = presentation.Slides(slide_number)
        
        # Add textbox (msoTextOrientationHorizontal = 1)
        textbox = slide.Shapes.AddTextbox(1, left, top, width, height)
        textbox.TextFrame.TextRange.Text = text
        
        # Apply formatting
        font = textbox.TextFrame.TextRange.Font
        
        if font_size:
            font.Size = font_size
        
        if font_color:
            rgb = int(font_color, 16)
            r = (rgb >> 16) & 0xFF
            g = (rgb >> 8) & 0xFF
            b = rgb & 0xFF
            font.Color.RGB = r + (g << 8) + (b << 16)
        
        if bold:
            font.Bold = True
        
        # Set alignment
        textbox.TextFrame.TextRange.ParagraphFormat.Alignment = ALIGN.get(align.lower(), 1)
        
        # Make textbox background transparent
        textbox.Fill.Visible = False
        textbox.Line.Visible = False
        
        return f"Added textbox to slide {slide_number}: \"{text[:30]}...\" (shape: {textbox.Name})"
    
    except Exception as e:
        log_system(f"Error adding textbox: {e}", "ERR")
        return f"Error: {e}"


def ppt_create_business_slide(slide_number: int, title: str, points: List[str], 
                               highlight_point: int = None) -> str:
    """
    Creates a professional business case slide with title and bullet points.
    Automatically uses brand template styling. Perfect for executive summaries.
    
    Args:
        slide_number: 1-indexed slide number to modify (must exist).
        title: Slide title text.
        points: List of bullet point strings.
        highlight_point: Optional 1-indexed point to highlight (make bold/colored).
    
    Returns:
        Status message.
    """
    log_system(f"Creating business slide {slide_number}: {title}", "PPT")
    
    if not COM_AVAILABLE:
        return "Error: PowerPoint COM automation not available"
    
    try:
        ppt = _get_ppt_app()
        if not ppt or ppt.Presentations.Count == 0:
            return "Error: No presentation is open"
        
        presentation = ppt.ActivePresentation
        
        if slide_number > presentation.Slides.Count:
            return f"Error: Slide {slide_number} does not exist"
        
        slide = presentation.Slides(slide_number)
        
        # Set title
        if slide.Shapes.HasTitle:
            slide.Shapes.Title.TextFrame.TextRange.Text = title
        
        # Find content placeholder
        content_shape = None
        for shape in slide.Shapes:
            if "content" in shape.Name.lower() or "text" in shape.Name.lower():
                if shape.HasTextFrame:
                    content_shape = shape
                    break
        
        if not content_shape:
            # Use first text shape that's not title
            for shape in slide.Shapes:
                if shape.HasTextFrame and shape != slide.Shapes.Title:
                    content_shape = shape
                    break
        
        if content_shape:
            # Build bullet text with proper line breaks
            bullet_text = "\n".join([f"• {point}" for point in points])
            content_shape.TextFrame.TextRange.Text = bullet_text
            
            # Highlight specific point if requested
            if highlight_point and 1 <= highlight_point <= len(points):
                try:
                    # Find the paragraph and make it bold
                    para = content_shape.TextFrame.TextRange.Paragraphs(highlight_point)
                    para.Font.Bold = True
                except:
                    pass
        
        return f"Created business slide {slide_number}: '{title}' with {len(points)} points"
    
    except Exception as e:
        log_system(f"Error creating business slide: {e}", "ERR")
        return f"Error: {e}"


# Export all PPT tools
PPT_TOOLS = {
    "ppt_get_active_presentation": ppt_get_active_presentation,
    "ppt_open_presentation": ppt_open_presentation,
    "ppt_get_slide_info": ppt_get_slide_info,
    "ppt_edit_text": ppt_edit_text,
    "ppt_add_slide": ppt_add_slide,
    "ppt_duplicate_slide": ppt_duplicate_slide,
    "ppt_delete_slide": ppt_delete_slide,
    "ppt_save_presentation": ppt_save_presentation,
    "ppt_goto_slide": ppt_goto_slide,
    "ppt_add_picture": ppt_add_picture,
    "ppt_add_shape": ppt_add_shape,
    "ppt_move_shape": ppt_move_shape,
    "ppt_resize_shape": ppt_resize_shape,
    "ppt_format_text": ppt_format_text,
    "ppt_get_theme_colors": ppt_get_theme_colors,
    # New advanced tools for impressive presentations
    "ppt_add_table": ppt_add_table,
    "ppt_set_shape_style": ppt_set_shape_style,
    "ppt_add_textbox": ppt_add_textbox,
    "ppt_create_business_slide": ppt_create_business_slide,
}

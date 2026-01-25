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


def ppt_open_presentation(file_path: str) -> str:
    """
    Opens a PowerPoint presentation file.
    
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


# Export all PPT tools
PPT_TOOLS = {
    "ppt_open_presentation": ppt_open_presentation,
    "ppt_get_slide_info": ppt_get_slide_info,
    "ppt_edit_text": ppt_edit_text,
    "ppt_add_slide": ppt_add_slide,
    "ppt_duplicate_slide": ppt_duplicate_slide,
    "ppt_delete_slide": ppt_delete_slide,
    "ppt_save_presentation": ppt_save_presentation,
    "ppt_goto_slide": ppt_goto_slide,
}

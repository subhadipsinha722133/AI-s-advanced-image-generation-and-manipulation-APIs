import streamlit as st
import os
from dotenv import load_dotenv
from services import (
    lifestyle_shot_by_image,
    lifestyle_shot_by_text,
    add_shadow,
    create_packshot,
    enhance_prompt,
    generative_fill,
    generate_hd_image,
    erase_foreground
)
from PIL import Image
import io
from io import BytesIO
import base64
import requests
import json
import time
import base64
from streamlit_drawable_canvas import st_canvas
import numpy as np
from services.erase_foreground import erase_foreground

# Configure Streamlit page
st.set_page_config(
    page_title="AdSnap Studio",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load environment variables
print("Loading environment variables...")
load_dotenv(verbose=True)  # Add verbose=True to see loading details

# Debug: Print environment variable status
api_key = os.getenv("BRIA_API_KEY")
print(f"API Key present: {bool(api_key)}")
print(f"API Key value: {api_key if api_key else 'Not found'}")
print(f"Current working directory: {os.getcwd()}")
print(f".env file exists: {os.path.exists('.env')}")

def initialize_session_state():
    """Initialize session state variables."""
    if 'api_key' not in st.session_state:
        st.session_state.api_key = os.getenv('BRIA_API_KEY')
    if 'generated_images' not in st.session_state:
        st.session_state.generated_images = []
    if 'current_image' not in st.session_state:
        st.session_state.current_image = None
    if 'pending_urls' not in st.session_state:
        st.session_state.pending_urls = []
    if 'edited_image' not in st.session_state:
        st.session_state.edited_image = None
    if 'original_prompt' not in st.session_state:
        st.session_state.original_prompt = ""
    if 'enhanced_prompt' not in st.session_state:
        st.session_state.enhanced_prompt = None

def download_image(url):
    """Download image from URL and return as bytes."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.content
    except Exception as e:
        st.error(f"Error downloading image: {str(e)}")
        return None

def apply_image_filter(image, filter_type):
    """Apply various filters to the image."""
    try:
        img = Image.open(io.BytesIO(image)) if isinstance(image, bytes) else Image.open(image)
        
        if filter_type == "Grayscale":
            return img.convert('L')
        elif filter_type == "Sepia":
            width, height = img.size
            pixels = img.load()
            for x in range(width):
                for y in range(height):
                    r, g, b = img.getpixel((x, y))[:3]
                    tr = int(0.393 * r + 0.769 * g + 0.189 * b)
                    tg = int(0.349 * r + 0.686 * g + 0.168 * b)
                    tb = int(0.272 * r + 0.534 * g + 0.131 * b)
                    img.putpixel((x, y), (min(tr, 255), min(tg, 255), min(tb, 255)))
            return img
        elif filter_type == "High Contrast":
            return img.point(lambda x: x * 1.5)
        elif filter_type == "Blur":
            return img.filter(Image.BLUR)
        else:
            return img
    except Exception as e:
        st.error(f"Error applying filter: {str(e)}")
        return None

def check_generated_images():
    """Check if pending images are ready and update the display."""
    if st.session_state.pending_urls:
        ready_images = []
        still_pending = []
        
        for url in st.session_state.pending_urls:
            try:
                response = requests.head(url)
                # Consider an image ready if we get a 200 response with any content length
                if response.status_code == 200:
                    ready_images.append(url)
                else:
                    still_pending.append(url)
            except Exception as e:
                still_pending.append(url)
        
        # Update the pending URLs list
        st.session_state.pending_urls = still_pending
        
        # If we found any ready images, update the display
        if ready_images:
            st.session_state.edited_image = ready_images[0]  # Display the first ready image
            if len(ready_images) > 1:
                st.session_state.generated_images = ready_images  # Store all ready images
            return True
            
    return False

def auto_check_images(status_container):
    """Automatically check for image completion a few times."""
    max_attempts = 3
    attempt = 0
    while attempt < max_attempts and st.session_state.pending_urls:
        time.sleep(2)  # Wait 2 seconds between checks
        if check_generated_images():
            status_container.success("✨ Image ready!")
            return True
        attempt += 1
    return False

def main():
    st.title("AdSnap Studio")
    initialize_session_state()
    
    # Sidebar for API key
    with st.sidebar:
        st.header("Settings")
        api_key = st.text_input("Enter your API key:", value=st.session_state.api_key if st.session_state.api_key else "", type="password")
        if api_key:
            st.session_state.api_key = api_key

    # Main tabs
    tabs = st.tabs([
        "🎨 Generate Image",
        "🖼️ Lifestyle Shot",
        "🎨 Generative Fill",
        "🎨 Erase Elements"
    ])
    
    # Generate Images Tab
    with tabs[0]:
        st.header("Generate Images")
        
        col1, col2 = st.columns([2, 1])
        with col1:
            # Prompt input
            prompt = st.text_area("Enter your prompt", 
                                value="",
                                height=100,
                                key="prompt_input")
            
            # Store original prompt in session state when it changes
            if "original_prompt" not in st.session_state:
                st.session_state.original_prompt = prompt
            elif prompt != st.session_state.original_prompt:
                st.session_state.original_prompt = prompt
                st.session_state.enhanced_prompt = None  # Reset enhanced prompt when original changes
            
            # Enhanced prompt display
            if st.session_state.get('enhanced_prompt'):
                st.markdown("**Enhanced Prompt:**")
                st.markdown(f"*{st.session_state.enhanced_prompt}*")
            
            # Enhance Prompt button--------------------------------------------------
            if st.button("✨ Enhance Prompt", key="enhance_button"):
                if not prompt:
                    st.warning("Please enter a prompt to enhance.")
                else:
                    with st.spinner("Enhancing prompt..."):
                        try:
                            result = enhance_prompt(st.session_state.api_key, prompt)
                            if result:
                                st.session_state.enhanced_prompt = result
                                st.success("Prompt enhanced!")
                                st.rerun()  # ✅ FIXED
                        except Exception as e:
                            st.error(f"Error enhancing prompt: {str(e)}")

#    -------------------------------------------------------------------------------------                         
            # Debug information
            st.write("Debug - Session State:", {
                "original_prompt": st.session_state.get("original_prompt"),
                "enhanced_prompt": st.session_state.get("enhanced_prompt")
            })
        
        with col2:
            num_images = st.slider("Number of images", 1, 4, 1)
            aspect_ratio = st.selectbox("Aspect ratio", ["1:1", "16:9", "9:16", "4:3", "3:4"])
            enhance_img = st.checkbox("Enhance image quality", value=True)
            
            # Style options
            st.subheader("Style Options")
            style = st.selectbox("Image Style", [
                "Realistic", "Artistic", "Cartoon", "Sketch", 
                "Watercolor", "Oil Painting", "Digital Art"
            ])
            
            # Add style to prompt
            if style and style != "Realistic":
                prompt = f"{prompt}, in {style.lower()} style"
        
        # Generate button
        if st.button("🎨 Generate Images", type="primary"):
            if not st.session_state.api_key:
                st.error("Please enter your API key in the sidebar.")
                return
                
            with st.spinner("🎨 Generating your masterpiece..."):
                try:
                    # Convert aspect ratio to proper format
                    result = generate_hd_image(
                        prompt=st.session_state.enhanced_prompt or prompt,
                        api_key=st.session_state.api_key,
                        num_results=num_images,
                        aspect_ratio=aspect_ratio,  # Already in correct format (e.g. "1:1")
                        sync=True,  # Wait for results
                        enhance_image=enhance_img,
                        medium="art" if style != "Realistic" else "photography",
                        prompt_enhancement=False,  # We're already using our own prompt enhancement
                        content_moderation=True  # Enable content moderation by default
                    )
                    
                    if result:
                        # Debug logging
                        st.write("Debug - Raw API Response:", result)
                        
                        if isinstance(result, dict):
                            if "result_url" in result:
                                st.session_state.edited_image = result["result_url"]
                                st.success("✨ Image generated successfully!")
                            elif "result_urls" in result:
                                st.session_state.edited_image = result["result_urls"][0]
                                st.success("✨ Image generated successfully!")
                            elif "result" in result and isinstance(result["result"], list):
                                for item in result["result"]:
                                    if isinstance(item, dict) and "urls" in item:
                                        st.session_state.edited_image = item["urls"][0]
                                        st.success("✨ Image generated successfully!")
                                        break
                                    elif isinstance(item, list) and len(item) > 0:
                                        st.session_state.edited_image = item[0]
                                        st.success("✨ Image generated successfully!")
                                        break
                        else:
                            st.error("No valid result format found in the API response.")
                            
                except Exception as e:
                    st.error(f"Error generating images: {str(e)}")
                    st.write("Full error:", str(e))
    
    # Product Photography Tab
    with tabs[1]:
        st.header("Product Photography")
        
        uploaded_file = st.file_uploader("Upload Product Image", type=["png", "jpg", "jpeg"], key="product_upload")
        if uploaded_file:
            col1, col2 = st.columns(2)
            
            with col1:
                st.image(uploaded_file, caption="Original Image", use_column_width=True)
                
                # Product editing options
                edit_option = st.selectbox("Select Edit Option", [
                    "Create Packshot",
                    "Add Shadow",
                    "Lifestyle Shot"
                ])
                
                if edit_option == "Create Packshot":
                    col_a, col_b = st.columns(2)
                    with col_a:
                        bg_color = st.color_picker("Background Color", "#FFFFFF")
                        sku = st.text_input("SKU (optional)", "")
                    with col_b:
                        force_rmbg = st.checkbox("Force Background Removal", False)
                        content_moderation = st.checkbox("Enable Content Moderation", False)
                    
                    if st.button("Create Packshot"):
                        with st.spinner("Creating professional packshot..."):
                            try:
                                # First remove background if needed
                                if force_rmbg:
                                    from services.background_service import remove_background
                                    bg_result = remove_background(
                                        st.session_state.api_key,
                                        uploaded_file.getvalue(),
                                        content_moderation=content_moderation
                                    )
                                    if bg_result and "result_url" in bg_result:
                                        # Download the background-removed image
                                        response = requests.get(bg_result["result_url"])
                                        if response.status_code == 200:
                                            image_data = response.content
                                        else:
                                            st.error("Failed to download background-removed image")
                                            return
                                    else:
                                        st.error("Background removal failed")
                                        return
                                else:
                                    image_data = uploaded_file.getvalue()
                                
                                # Now create packshot
                                result = create_packshot(
                                    st.session_state.api_key,
                                    image_data,
                                    background_color=bg_color,
                                    sku=sku if sku else None,
                                    force_rmbg=force_rmbg,
                                    content_moderation=content_moderation
                                )
                                
                                if result and "result_url" in result:
                                    st.success("✨ Packshot created successfully!")
                                    st.session_state.edited_image = result["result_url"]
                                else:
                                    st.error("No result URL in the API response. Please try again.")
                            except Exception as e:
                                st.error(f"Error creating packshot: {str(e)}")
                                if "422" in str(e):
                                    st.warning("Content moderation failed. Please ensure the image is appropriate.")
                
                elif edit_option == "Add Shadow":
                    col_a, col_b = st.columns(2)
                    with col_a:
                        shadow_type = st.selectbox("Shadow Type", ["Natural", "Drop"])
                        bg_color = st.color_picker("Background Color (optional)", "#FFFFFF")
                        use_transparent_bg = st.checkbox("Use Transparent Background", True)
                        shadow_color = st.color_picker("Shadow Color", "#000000")
                        sku = st.text_input("SKU (optional)", "")
                        
                        # Shadow offset
                        st.subheader("Shadow Offset")
                        offset_x = st.slider("X Offset", -50, 50, 0)
                        offset_y = st.slider("Y Offset", -50, 50, 15)
                    
                    with col_b:
                        shadow_intensity = st.slider("Shadow Intensity", 0, 100, 60)
                        shadow_blur = st.slider("Shadow Blur", 0, 50, 15 if shadow_type.lower() == "regular" else 20)
                        
                        # Float shadow specific controls
                        if shadow_type == "Float":
                            st.subheader("Float Shadow Settings")
                            shadow_width = st.slider("Shadow Width", -100, 100, 0)
                            shadow_height = st.slider("Shadow Height", -100, 100, 70)
                        
                        force_rmbg = st.checkbox("Force Background Removal", False)
                        content_moderation = st.checkbox("Enable Content Moderation", False)
                    
                    if st.button("Add Shadow"):
                        with st.spinner("Adding shadow effect..."):
                            try:
                                result = add_shadow(
                                    api_key=st.session_state.api_key,
                                    image_data=uploaded_file.getvalue(),
                                    shadow_type=shadow_type.lower(),
                                    background_color=None if use_transparent_bg else bg_color,
                                    shadow_color=shadow_color,
                                    shadow_offset=[offset_x, offset_y],
                                    shadow_intensity=shadow_intensity,
                                    shadow_blur=shadow_blur,
                                    shadow_width=shadow_width if shadow_type == "Float" else None,
                                    shadow_height=shadow_height if shadow_type == "Float" else 70,
                                    sku=sku if sku else None,
                                    force_rmbg=force_rmbg,
                                    content_moderation=content_moderation
                                )
                                
                                if result and "result_url" in result:
                                    st.success("✨ Shadow added successfully!")
                                    st.session_state.edited_image = result["result_url"]
                                else:
                                    st.error("No result URL in the API response. Please try again.")
                            except Exception as e:
                                st.error(f"Error adding shadow: {str(e)}")
                                if "422" in str(e):
                                    st.warning("Content moderation failed. Please ensure the image is appropriate.")
                
                elif edit_option == "Lifestyle Shot":
                    shot_type = st.radio("Shot Type", ["Text Prompt", "Reference Image"])
                    
                    # Common settings for both types
                    col1, col2 = st.columns(2)
                    with col1:
                        placement_type = st.selectbox("Placement Type", [
                            "Original", "Automatic", "Manual Placement",
                            "Manual Padding", "Custom Coordinates"
                        ])
                        num_results = st.slider("Number of Results", 1, 8, 4)
                        sync_mode = st.checkbox("Synchronous Mode", False,
                            help="Wait for results instead of getting URLs immediately")
                        original_quality = st.checkbox("Original Quality", False,
                            help="Maintain original image quality")
                        
                        if placement_type == "Manual Placement":
                            positions = st.multiselect("Select Positions", [
                                "Upper Left", "Upper Right", "Bottom Left", "Bottom Right",
                                "Right Center", "Left Center", "Upper Center",
                                "Bottom Center", "Center Vertical", "Center Horizontal"
                            ], ["Upper Left"])
                        
                        elif placement_type == "Manual Padding":
                            st.subheader("Padding Values (pixels)")
                            pad_left = st.number_input("Left Padding", 0, 1000, 0)
                            pad_right = st.number_input("Right Padding", 0, 1000, 0)
                            pad_top = st.number_input("Top Padding", 0, 1000, 0)
                            pad_bottom = st.number_input("Bottom Padding", 0, 1000, 0)
                        
                        elif placement_type in ["Automatic", "Manual Placement", "Custom Coordinates"]:
                            st.subheader("Shot Size")
                            shot_width = st.number_input("Width", 100, 2000, 1000)
                            shot_height = st.number_input("Height", 100, 2000, 1000)
                    
                    with col2:
                        if placement_type == "Custom Coordinates":
                            st.subheader("Product Position")
                            fg_width = st.number_input("Product Width", 50, 1000, 500)
                            fg_height = st.number_input("Product Height", 50, 1000, 500)
                            fg_x = st.number_input("X Position", -500, 1500, 0)
                            fg_y = st.number_input("Y Position", -500, 1500, 0)
                        
                        sku = st.text_input("SKU (optional)")
                        force_rmbg = st.checkbox("Force Background Removal", False)
                        content_moderation = st.checkbox("Enable Content Moderation", False)
                        
                        if shot_type == "Text Prompt":
                            fast_mode = st.checkbox("Fast Mode", True,
                                help="Balance between speed and quality")
                            optimize_desc = st.checkbox("Optimize Description", True,
                                help="Enhance scene description using AI")
                            if not fast_mode:
                                exclude_elements = st.text_area("Exclude Elements (optional)",
                                    help="Elements to exclude from the generated scene")
                        else:  # Reference Image
                            enhance_ref = st.checkbox("Enhance Reference Image", True,
                                help="Improve lighting, shadows, and texture")
                            ref_influence = st.slider("Reference Influence", 0.0, 1.0, 1.0,
                                help="Control similarity to reference image")
                    
                    if shot_type == "Text Prompt":
                        prompt = st.text_area("Describe the environment")
                        if st.button("Generate Lifestyle Shot") and prompt:
                            with st.spinner("Generating lifestyle shot..."):
                                try:
                                    # Convert placement selections to API format
                                    if placement_type == "Manual Placement":
                                        manual_placements = [p.lower().replace(" ", "_") for p in positions]
                                    else:
                                        manual_placements = ["upper_left"]
                                    
                                    result = lifestyle_shot_by_text(
                                        api_key=st.session_state.api_key,
                                        image_data=uploaded_file.getvalue(),
                                        scene_description=prompt,
                                        placement_type=placement_type.lower().replace(" ", "_"),
                                        num_results=num_results,
                                        sync=sync_mode,
                                        fast=fast_mode,
                                        optimize_description=optimize_desc,
                                        shot_size=[shot_width, shot_height] if placement_type != "Original" else [1000, 1000],
                                        original_quality=original_quality,
                                        exclude_elements=exclude_elements if not fast_mode else None,
                                        manual_placement_selection=manual_placements,
                                        padding_values=[pad_left, pad_right, pad_top, pad_bottom] if placement_type == "Manual Padding" else [0, 0, 0, 0],
                                        foreground_image_size=[fg_width, fg_height] if placement_type == "Custom Coordinates" else None,
                                        foreground_image_location=[fg_x, fg_y] if placement_type == "Custom Coordinates" else None,
                                        force_rmbg=force_rmbg,
                                        content_moderation=content_moderation,
                                        sku=sku if sku else None
                                    )
                                    
                                    if result:
                                        # Debug logging
                                        st.write("Debug - Raw API Response:", result)
                                        
                                        if sync_mode:
                                            if isinstance(result, dict):
                                                if "result_url" in result:
                                                    st.session_state.edited_image = result["result_url"]
                                                    st.success("✨ Image generated successfully!")
                                                elif "result_urls" in result:
                                                    st.session_state.edited_image = result["result_urls"][0]
                                                    st.success("✨ Image generated successfully!")
                                                elif "result" in result and isinstance(result["result"], list):
                                                    for item in result["result"]:
                                                        if isinstance(item, dict) and "urls" in item:
                                                            st.session_state.edited_image = item["urls"][0]
                                                            st.success("✨ Image generated successfully!")
                                                            break
                                                        elif isinstance(item, list) and len(item) > 0:
                                                            st.session_state.edited_image = item[0]
                                                            st.success("✨ Image generated successfully!")
                                                            break
                                                elif "urls" in result:
                                                    st.session_state.edited_image = result["urls"][0]
                                                    st.success("✨ Image generated successfully!")
                                        else:
                                            urls = []
                                            if isinstance(result, dict):
                                                if "urls" in result:
                                                    urls.extend(result["urls"][:num_results])  # Limit to requested number
                                                elif "result" in result and isinstance(result["result"], list):
                                                    # Process each result item
                                                    for item in result["result"]:
                                                        if isinstance(item, dict) and "urls" in item:
                                                            urls.extend(item["urls"])
                                                        elif isinstance(item, list):
                                                            urls.extend(item)
                                                        # Break if we have enough URLs
                                                        if len(urls) >= num_results:
                                                            break
                                                    
                                                    # Trim to requested number
                                                    urls = urls[:num_results]
                                            
                                            if urls:
                                                st.session_state.pending_urls = urls
                                                
                                                # Create a container for status messages
                                                status_container = st.empty()
                                                refresh_container = st.empty()
                                                
                                                # Show initial status
                                                status_container.info(f"🎨 Generation started! Waiting for {len(urls)} image{'s' if len(urls) > 1 else ''}...")
                                                
                                                # Try automatic checking first
                                                if auto_check_images(status_container):
                                                    st.experimental_rerun()
                                                
                                                # Add refresh button for manual checking
                                                if refresh_container.button("🔄 Check for Generated Images"):
                                                    with st.spinner("Checking for completed images..."):
                                                        if check_generated_images():
                                                            status_container.success("✨ Image ready!")
                                                            st.experimental_rerun()
                                                        else:
                                                            status_container.warning(f"⏳ Still generating your image{'s' if len(urls) > 1 else ''}... Please check again in a moment.")
                                except Exception as e:
                                    st.error(f"Error: {str(e)}")
                                    if "422" in str(e):
                                        st.warning("Content moderation failed. Please ensure the content is appropriate.")
                    else:
                        ref_image = st.file_uploader("Upload Reference Image", type=["png", "jpg", "jpeg"], key="ref_upload")
                        if st.button("Generate Lifestyle Shot") and ref_image:
                            with st.spinner("Generating lifestyle shot..."):
                                try:
                                    # Convert placement selections to API format
                                    if placement_type == "Manual Placement":
                                        manual_placements = [p.lower().replace(" ", "_") for p in positions]
                                    else:
                                        manual_placements = ["upper_left"]
                                    
                                    result = lifestyle_shot_by_image(
                                        api_key=st.session_state.api_key,
                                        image_data=uploaded_file.getvalue(),
                                        reference_image=ref_image.getvalue(),
                                        placement_type=placement_type.lower().replace(" ", "_"),
                                        num_results=num_results,
                                        sync=sync_mode,
                                        shot_size=[shot_width, shot_height] if placement_type != "Original" else [1000, 1000],
                                        original_quality=original_quality,
                                        manual_placement_selection=manual_placements,
                                        padding_values=[pad_left, pad_right, pad_top, pad_bottom] if placement_type == "Manual Padding" else [0, 0, 0, 0],
                                        foreground_image_size=[fg_width, fg_height] if placement_type == "Custom Coordinates" else None,
                                        foreground_image_location=[fg_x, fg_y] if placement_type == "Custom Coordinates" else None,
                                        force_rmbg=force_rmbg,
                                        content_moderation=content_moderation,
                                        sku=sku if sku else None,
                                        enhance_ref_image=enhance_ref,
                                        ref_image_influence=ref_influence
                                    )
                                    
                                    if result:
                                        # Debug logging
                                        st.write("Debug - Raw API Response:", result)
                                        
                                        if sync_mode:
                                            if isinstance(result, dict):
                                                if "result_url" in result:
                                                    st.session_state.edited_image = result["result_url"]
                                                    st.success("✨ Image generated successfully!")
                                                elif "result_urls" in result:
                                                    st.session_state.edited_image = result["result_urls"][0]
                                                    st.success("✨ Image generated successfully!")
                                                elif "result" in result and isinstance(result["result"], list):
                                                    for item in result["result"]:
                                                        if isinstance(item, dict) and "urls" in item:
                                                            st.session_state.edited_image = item["urls"][0]
                                                            st.success("✨ Image generated successfully!")
                                                            break
                                                        elif isinstance(item, list) and len(item) > 0:
                                                            st.session_state.edited_image = item[0]
                                                            st.success("✨ Image generated successfully!")
                                                            break
                                                elif "urls" in result:
                                                    st.session_state.edited_image = result["urls"][0]
                                                    st.success("✨ Image generated successfully!")
                                        else:
                                            urls = []
                                            if isinstance(result, dict):
                                                if "urls" in result:
                                                    urls.extend(result["urls"][:num_results])  # Limit to requested number
                                                elif "result" in result and isinstance(result["result"], list):
                                                    # Process each result item
                                                    for item in result["result"]:
                                                        if isinstance(item, dict) and "urls" in item:
                                                            urls.extend(item["urls"])
                                                        elif isinstance(item, list):
                                                            urls.extend(item)
                                                        # Break if we have enough URLs
                                                        if len(urls) >= num_results:
                                                            break
                                                    
                                                    # Trim to requested number
                                                    urls = urls[:num_results]
                                            
                                            if urls:
                                                st.session_state.pending_urls = urls
                                                
                                                # Create a container for status messages
                                                status_container = st.empty()
                                                refresh_container = st.empty()
                                                
                                                # Show initial status
                                                status_container.info(f"🎨 Generation started! Waiting for {len(urls)} image{'s' if len(urls) > 1 else ''}...")
                                                
                                                # Try automatic checking first
                                                if auto_check_images(status_container):
                                                    st.experimental_rerun()
                                                
                                                # Add refresh button for manual checking
                                                if refresh_container.button("🔄 Check for Generated Images"):
                                                    with st.spinner("Checking for completed images..."):
                                                        if check_generated_images():
                                                            status_container.success("✨ Image ready!")
                                                            st.experimental_rerun()
                                                        else:
                                                            status_container.warning(f"⏳ Still generating your image{'s' if len(urls) > 1 else ''}... Please check again in a moment.")
                                except Exception as e:
                                    st.error(f"Error: {str(e)}")
                                    if "422" in str(e):
                                        st.warning("Content moderation failed. Please ensure the content is appropriate.")
            
            with col2:
                if st.session_state.edited_image:
                    st.image(st.session_state.edited_image, caption="Edited Image", use_column_width=True)
                    image_data = download_image(st.session_state.edited_image)
                    if image_data:
                        st.download_button(
                            "⬇️ Download Result",
                            image_data,
                            "edited_product.png",
                            "image/png"
                        )
                elif st.session_state.pending_urls:
                    st.info("Images are being generated. Click the refresh button above to check if they're ready.")

    # Generative Fill Tab-------------------------------------------------------------------------------------------------------------------------
    # --------------------------------------------------------------------
    with tabs[2]:
        st.header("🎨 Generative Fill")
        st.markdown("Draw a mask on the image and describe what you want to generate in that area.")
        
        uploaded_file = st.file_uploader("Upload Image", type=["png", "jpg", "jpeg"], key="fill_upload")
        if uploaded_file:
            # Create columns for original image and canvas
            col1, col2 = st.columns(2)
            
            with col1:
                # Display original image
                st.image(uploaded_file, caption="Original Image", use_column_width=True)
                
                # Get image dimensions for canvas
                img = Image.open(uploaded_file)
                img_width, img_height = img.size
                
                # Calculate aspect ratio and set canvas height
                aspect_ratio = img_height / img_width
                canvas_width = min(img_width, 800)  # Max width of 800px
                canvas_height = int(canvas_width * aspect_ratio)
                
                # Resize image to match canvas dimensions
                img = img.resize((canvas_width, canvas_height))
                
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Convert to numpy array with proper shape and type
                img_array = np.array(img).astype(np.uint8)
                
                # Add drawing canvas using Streamlit's drawing canvas component
                stroke_width = st.slider("Brush width", 1, 50, 20)
                stroke_color = st.color_picker("Brush color", "#fff")
                drawing_mode = "freedraw"


                
                
                # Create canvas with background image
                canvas_result = st_canvas(
                    fill_color="rgba(255, 255, 255, 0.0)",  # Transparent fill
                    stroke_width=stroke_width,
                    stroke_color=stroke_color,
                    drawing_mode=drawing_mode,
                    background_color="",  # Transparent background
                    background_image=img_array if img_array.shape[-2] == 5 else None,  # Only pass RGB images
                    height=canvas_height,
                    width=canvas_width,
                    key="canvas",
                )
                



                # Options for generation
                st.subheader("Generation Options")
                prompt = st.text_area("Describe what to generate in the masked area")
                negative_prompt = st.text_area("Describe what to avoid (optional)")
                
                col_a, col_b = st.columns(2)
                with col_a:
                    num_results = st.slider("Number of variations", 1, 4, 1)
                    sync_mode = st.checkbox("Synchronous Mode", False,
                        help="Wait for results instead of getting URLs immediately",
                        key="gen_fill_sync_mode")
                
                with col_b:
                    seed = st.number_input("Seed (optional)", min_value=0, value=0,
                        help="Use same seed to reproduce results")
                    content_moderation = st.checkbox("Enable Content Moderation", False,
                        key="gen_fill_content_mod")
                
                if st.button("🎨 Generate", type="primary"):
                    if not prompt:
                        st.error("Please enter a prompt describing what to generate.")
                        return
                    
                    if canvas_result.image_data is None:
                        st.error("Please draw a mask on the image first.")
                        return
                    
                    # Convert canvas result to mask
                    mask_img = Image.fromarray(canvas_result.image_data.astype('uint8'), mode='RGBA')
                    mask_img = mask_img.convert('L')
                    
                    # Convert mask to bytes
                    mask_bytes = io.BytesIO()
                    mask_img.save(mask_bytes, format='PNG')
                    mask_bytes = mask_bytes.getvalue()
                    
                    # Convert uploaded image to bytes
                    image_bytes = uploaded_file.getvalue()
                    
                    with st.spinner("🎨 Generating..."):
                        try:
                            result = generative_fill(
                                st.session_state.api_key,
                                image_bytes,
                                mask_bytes,
                                prompt,
                                negative_prompt=negative_prompt if negative_prompt else None,
                                num_results=num_results,
                                sync=sync_mode,
                                seed=seed if seed != 0 else None,
                                content_moderation=content_moderation
                            )
                            
                            if result:
                                st.write("Debug - API Response:", result)
                                
                                if sync_mode:
                                    if "urls" in result and result["urls"]:
                                        st.session_state.edited_image = result["urls"][0]
                                        if len(result["urls"]) > 1:
                                            st.session_state.generated_images = result["urls"]
                                        st.success("✨ Generation complete!")
                                    elif "result_url" in result:
                                        st.session_state.edited_image = result["result_url"]
                                        st.success("✨ Generation complete!")
                                else:
                                    if "urls" in result:
                                        st.session_state.pending_urls = result["urls"][:num_results]
                                        
                                        # Create containers for status
                                        status_container = st.empty()
                                        refresh_container = st.empty()
                                        
                                        # Show initial status
                                        status_container.info(f"🎨 Generation started! Waiting for {len(st.session_state.pending_urls)} image{'s' if len(st.session_state.pending_urls) > 1 else ''}...")
                                        
                                        # Try automatic checking
                                        if auto_check_images(status_container):
                                            st.rerun()
                                        
                                        # Add refresh button
                                        if refresh_container.button("🔄 Check for Generated Images"):
                                            if check_generated_images():
                                                status_container.success("✨ Images ready!")
                                                st.rerun()
                                            else:
                                                status_container.warning("⏳ Still generating... Please check again in a moment.")
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
                            st.write("Full error details:", str(e))
            
            with col2:
                if st.session_state.edited_image:
                    st.image(st.session_state.edited_image, caption="Generated Result", use_column_width=True)
                    image_data = download_image(st.session_state.edited_image)
                    if image_data:
                        st.download_button(
                            "⬇️ Download Result",
                            image_data,
                            "generated_fill.png",
                            "image/png"
                        )
                elif st.session_state.pending_urls:
                    st.info("Generation in progress. Click the refresh button above to check status.")
# -----------------------------------------------------------------------------------------------------------

    # Erase Elements Tab
    with tabs[3]:
        st.header("🎨 Erase Elements")
        st.markdown("Upload an image and select the area you want to erase.")
        
        uploaded_file = st.file_uploader("Upload Image", type=["png", "jpg", "jpeg"], key="erase_upload")
        if uploaded_file:
            col1, col2 = st.columns(2)
            
            with col1:
                # Display original image
                st.image(uploaded_file, caption="Original Image", use_column_width=True)
                
                # Get image dimensions for canvas
                img = Image.open(uploaded_file)
                img_width, img_height = img.size
                
                # Calculate aspect ratio and set canvas height
                aspect_ratio = img_height / img_width
                canvas_width = min(img_width, 500)  # Max width of 800px
                canvas_height = int(canvas_width * aspect_ratio)
                
                # Resize image to match canvas dimensions
                img = img.resize((canvas_width, canvas_height))
                
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')

                # import base64
                # from io import BytesIO


                img_array=np.array(img)

                

                # Add drawing canvas using Streamlit's drawing canvas component
                stroke_width = st.slider("Brush width", 1, 50, 20, key="erase_brush_width")
                stroke_color = st.color_picker("Brush color", "#fff", key="erase_brush_color")



                canvas_result = st_canvas(
                        fill_color="rgba(255, 255, 255, 0.0)",
                        stroke_width=stroke_width,
                        stroke_color=stroke_color,
                        background_color="",
                        # background_image=img_array[1],  # First try with PIL Image
                        drawing_mode="freedraw",
                        height=canvas_height,
                        width=canvas_width,
                        key="erase_canvas",
                    )

                # try:
                #     canvas_result = st_canvas(
                #         fill_color="rgba(255, 255, 255, 0.0)",
                #         stroke_width=stroke_width,
                #         stroke_color=stroke_color,
                #         background_color="",
                #         background_image=img,  # First try with PIL Image
                #         drawing_mode="freedraw",
                #         height=canvas_height,
                #         width=canvas_width,
                #         key="erase_canvas",
                #     )



                # except:
                #     # Create canvas with background image
                #     canvas_result = st_canvas(
                #         fill_color="rgba(255, 255, 255, 0.0)",  # Transparent fill
                #         stroke_width=stroke_width,
                #         stroke_color=stroke_color,
                #         background_color="",  # Transparent background
                #         # background_image=img_array,  # Pass PIL Image directly
                #         background_image=img_array if img_array.shape[-2] == 5 else None, 
                #         drawing_mode="freedraw",
                #         height=canvas_height,
                #         width=canvas_width,
                #         key="erase_canvas",
                #     )







#  ----------------------------------------------------------------------               # 
                # Options for erasing
                st.subheader("Erase Options")
                content_moderation = st.checkbox("Enable Content Moderation", False, key="erase_content_mod")
                
                if st.button("🎨 Erase Selected Area", key="erase_btn"):
                    if not canvas_result.image_data is None:
                        with st.spinner("Erasing selected area..."):
                            try:
                                # Convert canvas result to mask
                                mask_img = Image.fromarray(canvas_result.image_data.astype('uint8'), mode='RGBA')
                                mask_img = mask_img.convert('L')
                                
                                # Convert uploaded image to bytes
                                image_bytes = uploaded_file.getvalue()
                                
                                result = erase_foreground(
                                    st.session_state.api_key,
                                    image_data=image_bytes,
                                    content_moderation=content_moderation
                                )
                                
                                if result:
                                    if "result_url" in result:
                                        st.session_state.edited_image = result["result_url"]
                                        st.success("✨ Area erased successfully!")
                                    else:
                                        st.error("No result URL in the API response. Please try again.")
                            except Exception as e:
                                st.error(f"Error: {str(e)}")
                                if "422" in str(e):
                                    st.warning("Content moderation failed. Please ensure the image is appropriate.")
                    else:
                        st.warning("Please draw on the image to select the area to erase.")
            
            with col2:
                

                if st.session_state.edited_image:
                    st.image(st.session_state.edited_image, caption="Result", use_column_width=True)
                    image_data = download_image(st.session_state.edited_image)
                    if image_data:
                        st.download_button(
                            "⬇️ Download Result",
                            image_data,
                            "erased_image.png",
                            "image/png",
                            key="erase_download"
                        )
            

if __name__ == "__main__":
    main() 








    

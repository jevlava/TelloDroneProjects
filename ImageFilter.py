import cv2
from djitellopy import tello

# Initialize the Tello drone object
me = tello.Tello()

# Connect to Tello over Wi-Fi
# wait_for_state=False prevents firewall issues from blocking execution
me.connect(wait_for_state=False)
print(f"Battery: {me.get_battery()}%")

# Start receiving video frames over UDP from the drone's front camera
me.streamon()

# Initialize variable to track which filter is currently active
# 0: Original, 1: Grayscale, 2: Canny Edges, 3: HSV, 4: Blur
filter_mode = 0

# Print control instructions in the terminal console
print("\n--- CONTROLS ---")
print("Press '0': Normal Feed")
print("Press '1': Grayscale Filter")
print("Press '2': Canny Edge Filter")
print("Press '3': HSV Filter")
print("Press '4': Gaussian Blur")
print("Press 'f': Cycle Filters")
print("Press 'q': Quit\n")

# Main video processing loop
while True:
    # -------------------------------------------------------------------------
    # 1. FRAME ACQUISITION & FORMAT FIXING
    # -------------------------------------------------------------------------
    # Retrieve the latest raw frame array from the Tello camera background thread
    img = me.get_frame_read().frame

    # DJITelloPy outputs RGB format, but OpenCV expects BGR format.
    # We must convert RGB -> BGR so skin tones and colors render correctly.
    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

    # Resize frame to standard width x height for consistent display performance
    img = cv2.resize(img, (640, 480))

    # -------------------------------------------------------------------------
    # 2. FILTER SELECTION LOGIC
    # -------------------------------------------------------------------------
    # Check the current filter mode state and apply the corresponding transformation
    if filter_mode == 0:
        processed_img = img  # Keep original color image
        filter_name = "Original (RGB)"

    elif filter_mode == 1:
        # Convert color image to single-channel grayscale (black & white)
        processed_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        filter_name = "Grayscale"

    elif filter_mode == 2:
        # First convert to grayscale, then pass through Canny algorithm to highlight edges
        # 100 and 200 are the low and high hysteresis thresholds for edge detection
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        processed_img = cv2.Canny(gray, 100, 200)
        filter_name = "Canny Edges"

    elif filter_mode == 3:
        # Convert BGR to HSV (Hue, Saturation, Value) color space
        # Useful for color tracking/isolation (e.g., detecting red/blue objects)
        processed_img = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        filter_name = "HSV"

    elif filter_mode == 4:
        # Apply Gaussian Blur filter to smooth images and reduce noise
        # (21, 21) is the kernel size (must be odd numbers); larger numbers = blurrier
        processed_img = cv2.GaussianBlur(img, (21, 21), 0)
        filter_name = "Gaussian Blur"

    # -------------------------------------------------------------------------
    # 3. ON-SCREEN DISPLAY (OSD) OVERLAY
    # -------------------------------------------------------------------------
    # Draw text directly onto the frame showing which filter is currently active
    # Parameters: image, text, position (x,y), font, scale, color (BGR), line thickness
    cv2.putText(processed_img, f"Filter: {filter_name}", (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

    # Render the processed frame inside a GUI window named "Tello Camera Feed"
    cv2.imshow("Tello Camera Feed", processed_img)

    # -------------------------------------------------------------------------
    # 4. KEYBOARD INTERRUPT & CONTROL HANDLING
    # -------------------------------------------------------------------------
    # Wait 1 millisecond for key press input. Masking with 0xFF ensures compatibility across operating systems.
    key = cv2.waitKey(1) & 0xFF

    # 'q' key breaks out of the while loop to terminate execution
    if key == ord('q'):
        break
    # Direct numeric keys to set specific filters
    elif key == ord('0'):
        filter_mode = 0
    elif key == ord('1'):
        filter_mode = 1
    elif key == ord('2'):
        filter_mode = 2
    elif key == ord('3'):
        filter_mode = 3
    elif key == ord('4'):
        filter_mode = 4
    # 'f' key cycles sequentially through filters 0 -> 1 -> 2 -> 3 -> 4 -> 0
    elif key == ord('f'):
        filter_mode = (filter_mode + 1) % 5

# -------------------------------------------------------------------------
# 5. CLEANUP & SHUTDOWN
# -------------------------------------------------------------------------
# Destroy all open OpenCV GUI windows to free up screen memory
cv2.destroyAllWindows()

# Signal Tello to stop broadcasting the video stream over UDP to save power/bandwidth
me.streamoff()
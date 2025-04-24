import requests
import time
import json
import sys
import textwrap

# --- Configuration ---
BASE_URL = "http://api.trytodecrypt.com/encrypt"
API_KEY = "<you-api-key>"
CHARS_TO_MAP = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-_.,;:?! "
REPETITION_COUNT = 50
REQUEST_TIMEOUT = 20
API_DELAY = 0.1
OUTPUT_WIDTH = 100

# --- Global State Variables ---
current_api_id = None
character_encryption_map = {}
encrypted_segment_length = None # Crucial for formatting matrix output
character_matrix_data = {}

# --- Helper Functions (get_api_id_from_user - remains the same) ---
def get_api_id_from_user():
    """Prompts the user to enter an API ID."""
    while True:
        user_input = input("Enter the API ID to use: ").strip()
        if user_input:
            return user_input
        else:
            print("API ID cannot be empty. Please try again.")


# --- Single Character Mapping & Decryption Functions (encrypt_and_build_map, decrypt_string - remains the same) ---
def encrypt_and_build_map(api_id):
    """
    Encrypts SINGLE characters for the given ID for DECRYPTION purposes.
    Determines the encrypted_segment_length.
    Returns the mapping dictionary and the segment length.
    """
    global character_encryption_map, encrypted_segment_length # Allow modification
    print(f"\n--- Starting SINGLE Character Encryption for Decryption Map (ID: {api_id}) ---")
    print(f"Encrypting {len(CHARS_TO_MAP)} unique characters...")

    # Reset state for the new ID before starting
    character_encryption_map = {}
    encrypted_segment_length = None
    temp_map = {}
    temp_segment_length = None # Local variable for length detection
    processed_chars = 0
    errors = 0

    for char in CHARS_TO_MAP:
        params = { 'key': API_KEY, 'id': api_id, 'text': char }
        try:
            response = requests.get(BASE_URL, params=params, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            encrypted_string = response.text.strip()

            if not encrypted_string:
                 print(f"    WARNING: Received empty response for char '{char}'. Skipping.")
                 errors += 1
                 continue

            # ---> Segment Length Detection and Consistency Check <---
            if temp_segment_length is None:
                temp_segment_length = len(encrypted_string)
                print(f"  Detected segment length: {temp_segment_length}") # Report detected length
            elif len(encrypted_string) != temp_segment_length:
                print(f"\n--- FATAL ERROR (Single Char Map) ---")
                print(f"Inconsistent encrypted string lengths detected for ID '{api_id}'.")
                print(f"Expected length {temp_segment_length}, got {len(encrypted_string)} for char '{char}'.")
                print("Decryption map generation failed. Cannot proceed reliably.")
                # Do not update global state on failure
                return None, None # Signal failure

            temp_map[char] = encrypted_string
            processed_chars += 1
            if processed_chars % 10 == 0 or processed_chars == len(CHARS_TO_MAP):
                 print(f"  Processed {processed_chars}/{len(CHARS_TO_MAP)} characters...")

            time.sleep(API_DELAY)

        except requests.exceptions.Timeout:
            print(f"    ERROR: Request timed out for char '{char}'")
            errors += 1
        except requests.exceptions.HTTPError as http_err:
            print(f"    ERROR: HTTP error for char '{char}': {http_err} (Status: {response.status_code})")
            errors += 1
        except requests.exceptions.RequestException as req_err:
            print(f"    ERROR: Request error for char '{char}': {req_err}")
            errors += 1
        except Exception as e:
             print(f"    ERROR: Unexpected error for char '{char}': {e}")
             errors += 1


    if errors > 0:
         print(f"\nWarning: Encountered {errors} errors during single char encryption.")
    if not temp_map or temp_segment_length is None or temp_segment_length == 0: # Added check for 0 length
        print(f"\nFailed to create a valid single character map or determine segment length for ID '{api_id}'.")
        return None, None

    print(f"--- Single Character Map Generated (ID: {api_id}) ---")
    print(f"Successfully mapped {len(temp_map)} characters for decryption.")
    print(f"Confirmed segment length for decryption: {temp_segment_length}")

    # Update global state only on full success
    character_encryption_map = temp_map
    encrypted_segment_length = temp_segment_length
    return character_encryption_map, encrypted_segment_length


def decrypt_string(encrypted_text):
    """
    Decrypts the given text using the current character_encryption_map.
    (Remains the same)
    """
    if not character_encryption_map:
        print("\nError: No decryption map available. Please generate it first (Option 1).")
        return
    # Check segment length specifically here
    if encrypted_segment_length is None or encrypted_segment_length <= 0:
        print("\nError: Cannot decrypt. Encrypted segment length unknown or invalid (<=0).")
        print("Ensure the Decryption Map was generated successfully (Option 1).")
        return

    print(f"\n--- Decrypting using map for ID: {current_api_id} ---")
    print(f"Encrypted text (length {len(encrypted_text)}):")
    print(textwrap.fill(encrypted_text, width=OUTPUT_WIDTH))
    print(f"Using segment length: {encrypted_segment_length}")

    try:
        decryption_map = {v: k for k, v in character_encryption_map.items()}
        if len(decryption_map) != len(character_encryption_map):
            print("Warning: Duplicate encrypted values detected in single-char map. Decryption might be ambiguous.")
    except Exception as e:
        print(f"Error creating reverse decryption map: {e}")
        return

    decrypted_chars = []
    unknown_segments = 0

    if len(encrypted_text) % encrypted_segment_length != 0:
        print("\nWarning: Encrypted text length is not a multiple of the detected segment length.")

    for i in range(0, len(encrypted_text), encrypted_segment_length):
        segment = encrypted_text[i : i + encrypted_segment_length]
        if len(segment) < encrypted_segment_length:
             print(f"  Skipping trailing incomplete segment: '{segment}'")
             break
        original_char = decryption_map.get(segment)
        if original_char is not None:
            decrypted_chars.append(original_char)
        else:
            decrypted_chars.append('?')
            if unknown_segments < 5:
                 print(f"  Warning: Unknown encrypted segment found: '{segment}'")
            elif unknown_segments == 5:
                 print("  (Further unknown segment warnings suppressed)")
            unknown_segments += 1

    decrypted_result = "".join(decrypted_chars)
    print("\n--- Decryption Result ---")
    print(f"Decrypted text: {decrypted_result}")
    if unknown_segments > 0:
        print(f"({unknown_segments} unknown segment(s) replaced with '?')")
    print("-" * (len("--- Decryption Result ---")))


# --- Matrix Generation Functions (encrypt_repeated_string, generate_all_matrices - remain the same) ---
def encrypt_repeated_string(api_id, char_to_repeat, count):
    """ Calls the API with a string of repeated characters. """
    input_text = char_to_repeat * count
    params = { 'key': API_KEY, 'id': api_id, 'text': input_text }
    try:
        response = requests.get(BASE_URL, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        encrypted_string = response.text.strip()
        if not encrypted_string:
             print(f"    WARNING: Received empty response for '{char_to_repeat}' * {count}. Treating as error.")
             return None
        return encrypted_string
    except requests.exceptions.Timeout:
        print(f"    ERROR: Request timed out for '{char_to_repeat}' * {count}")
        return None
    except requests.exceptions.HTTPError as http_err:
        print(f"    ERROR: HTTP error for '{char_to_repeat}' * {count}: {http_err} (Status: {response.status_code})")
        return None
    except requests.exceptions.RequestException as req_err:
        print(f"    ERROR: Request error for '{char_to_repeat}' * {count}: {req_err}")
        return None
    except Exception as e:
         print(f"    ERROR: Unexpected error for '{char_to_repeat}' * {count}: {e}")
         return None

def generate_all_matrices(api_id):
    """ Generates the encrypted data for repeated chars for the matrix display. """
    global character_matrix_data # Allow modification
    print(f"\n--- Generating Matrix Data (ID: {api_id}) ---")
    print(f"Encrypting {len(CHARS_TO_MAP)} characters, each repeated {REPETITION_COUNT} times...")

    # Clear previous matrix data for this ID before generating new
    character_matrix_data = {}
    temp_matrix_data = {}
    errors = 0
    success_count = 0

    for i, char in enumerate(CHARS_TO_MAP):
        print(f"  Processing char {i+1}/{len(CHARS_TO_MAP)}: '{char}' * {REPETITION_COUNT}")
        encrypted_result = encrypt_repeated_string(api_id, char, REPETITION_COUNT)

        if encrypted_result is not None:
            temp_matrix_data[char] = encrypted_result
            success_count += 1
        else:
            errors += 1

        time.sleep(API_DELAY)

    print(f"--- Matrix Data Generation Complete (ID: {api_id}) ---")
    print(f"Successfully generated data for {success_count} characters.")
    if errors > 0:
         print(f"Encountered {errors} errors during the process.")

    if not temp_matrix_data:
         print("Failed to generate any matrix data.")
         return False # Indicate failure
    else:
         character_matrix_data = temp_matrix_data # Update global state
         return True # Indicate success

# --- MODIFIED display_matrices function ---
def display_matrices():
    """
    Displays the generated matrix data, adding spaces between segments
    based on the globally stored encrypted_segment_length.
    """
    if not character_matrix_data:
        print("\nNo matrix data available. Please generate it first (Option 2).")
        return

    # Check if we have a valid segment length from Option 1
    if encrypted_segment_length is None or encrypted_segment_length <= 0:
        print("\nWarning: Encrypted segment length not determined or invalid.")
        print("Cannot format matrix output with spaces between segments.")
        print("Run Option 1 first to determine segment length for the current ID.")
        # Fallback to displaying raw data without spaces
        print(f"\n--- Character Matrix Data (ID: {current_api_id}) - RAW ---")
        print(f"(Shows encryption of char repeated {REPETITION_COUNT} times)")
        print("-" * 50)
        for char, encrypted_string in character_matrix_data.items():
             original_string = char * REPETITION_COUNT
             print(f"\nCharacter: '{char}'")
             print("Original String:")
             print(textwrap.fill(original_string, width=OUTPUT_WIDTH, initial_indent='  ', subsequent_indent='  '))
             print("Encrypted Result (Raw):")
             print(textwrap.fill(encrypted_string, width=OUTPUT_WIDTH, initial_indent='  ', subsequent_indent='  '))
             print("-" * 30)
        print("--- End of Matrix Data (Raw) ---")
        return # Exit function after showing raw data

    # Proceed with formatted output if segment length is valid
    print(f"\n--- Character Matrix Data (ID: {current_api_id}) - Formatted ---")
    print(f"(Shows encryption of char repeated {REPETITION_COUNT} times)")
    print(f"(Segment length: {encrypted_segment_length}, spaces added between segments)")
    print("-" * 60)

    for char, encrypted_string in character_matrix_data.items():
         original_string = char * REPETITION_COUNT
         print(f"\nCharacter: '{char}'")
         print("Original String:")
         print(textwrap.fill(original_string, width=OUTPUT_WIDTH, initial_indent='  ', subsequent_indent='  '))
         print("Encrypted Result (Formatted):")

         # --- Segment Splitting and Joining ---
         segments = []
         for i in range(0, len(encrypted_string), encrypted_segment_length):
             segment = encrypted_string[i : i + encrypted_segment_length]
             # Only add complete segments
             if len(segment) == encrypted_segment_length:
                 segments.append(segment)
             # Optional: Handle or report trailing partial segments if needed
             # elif segment: # If there's a non-empty partial segment left
             #     print(f"  (Note: Trailing partial segment '{segment}' ignored in formatted output)")

         formatted_encrypted_string = " ".join(segments)
         # --- End Segment Splitting ---

         print(textwrap.fill(formatted_encrypted_string, width=OUTPUT_WIDTH, initial_indent='  ', subsequent_indent='  ', break_long_words=False, break_on_hyphens=False)) # Adjust wrapping if needed
         print("-" * 30) # Separator for each character

    print("--- End of Matrix Data (Formatted) ---")


# --- Main Program Loop (main function remains the same) ---
def main():
    global current_api_id, encrypted_segment_length # Allow modification
    global character_matrix_data

    print("--- Interactive Encrypt/Decrypt & Matrix Program ---")

    while True:
        print("\n=========== Main Menu ===========")
        print(f"Current API ID: {current_api_id if current_api_id else 'Not Set'}")
        print(f"Decryption Map: {len(character_encryption_map)} chars mapped" if character_encryption_map else "No decryption map")
        print(f"Segment Length: {encrypted_segment_length}" if encrypted_segment_length is not None else "Not determined")
        print(f"Matrix Data:    {len(character_matrix_data)} chars generated" if character_matrix_data else "No matrix data")
        print("---------------------------------")
        print("1. Set/Change API ID & Generate Decryption Map (Determines Segment Length)") # Emphasize segment length
        print("2. Generate Character Matrix Data") # Removed 'Display' here
        print("3. Decrypt a String (using decryption map)")
        print("4. View Current Decryption Map")
        print("5. View Current Matrix Data (Formatted with spaces)") # Emphasize formatting
        print("6. Quit")
        print("=================================")

        choice = input("Enter your choice (1-6): ").strip()

        if choice == '1':
            new_id = get_api_id_from_user()
            # Clear old matrix data when changing ID and regenerating map
            # as the segment length might change
            if new_id != current_api_id:
                 print("API ID changed, clearing previous matrix data.")
                 character_matrix_data = {}

            map_result, len_result = encrypt_and_build_map(new_id)
            if map_result is not None and len_result is not None:
                 current_api_id = new_id # Update ID only on success
                 print(f"API ID set to '{current_api_id}', decryption map generated, segment length is {encrypted_segment_length}.")
            else:
                 print(f"Failed to generate decryption map for ID {new_id}. API ID *not* changed.")
                 # Keep old ID and potentially old map/segment length if map generation failed


        elif choice == '2':
            if current_api_id is None:
                print("\nPlease set an API ID first (Option 1).")
                continue
            if generate_all_matrices(current_api_id):
                 print("Matrix data generated successfully. Use Option 5 to view.")
            else:
                 print("Matrix data generation failed.")

        elif choice == '3':
             # Decrypt function already checks for map and segment length
             if current_api_id is None:
                  print("\nPlease set an API ID first (Option 1).")
                  continue
             encrypted_input = input("Enter the encrypted string to decrypt: ").strip()
             if encrypted_input:
                 decrypt_string(encrypted_input)
             else:
                 print("No encrypted string entered.")

        elif choice == '4':
            if character_encryption_map:
                 print("\n--- Current Decryption Map ---")
                 print(f"(Generated using ID: {current_api_id})")
                 print(f"(Detected segment length: {encrypted_segment_length})")
                 print(json.dumps(character_encryption_map, indent=4, ensure_ascii=False))
                 print("-----------------------------")
            else:
                 print("\nNo decryption map has been generated yet (Use Option 1).")

        elif choice == '5': # View Matrix Data
            if not current_api_id:
                 print("\nPlease set an API ID first (Option 1).")
            elif not character_matrix_data:
                 print("\nNo matrix data has been generated yet for this ID (Use Option 2).")
            else:
                 # Display matrices will handle checking for segment length internally
                 display_matrices()

        elif choice == '6':
            print("Exiting program.")
            sys.exit()

        else:
            print("Invalid choice. Please enter a number between 1 and 6.")

# --- Run the program ---
if __name__ == "__main__":
    main()

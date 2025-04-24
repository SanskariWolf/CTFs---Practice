use bmp::{Image, Pixel, BmpError};
use std::env;
use std::process;
use std::io::{self};

fn extract_lsb(img: &Image) -> io::Result<Vec<u8>> {
    let mut extracted_bits = Vec::new();
    let width = img.get_width();
    let height = img.get_height();

    for y in 0..height {
        for x in 0..width {
            let pixel: Pixel = img.get_pixel(x, y);
            extracted_bits.push(pixel.r & 1);
            extracted_bits.push(pixel.g & 1);
            extracted_bits.push(pixel.b & 1);
        }
    }

    let mut extracted_bytes = Vec::new();
    let mut current_byte: u8 = 0;
    let mut bit_count: u8 = 0;

    for bit in extracted_bits {
        current_byte |= bit << bit_count;
        bit_count += 1;
        if bit_count == 8 {
            extracted_bytes.push(current_byte);
            current_byte = 0;
            bit_count = 0;
        }
    }
    Ok(extracted_bytes)
}

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() != 2 {
        eprintln!("Usage: {} <input_bmp_file>", args[0]);
        process::exit(1);
    }
    let filename = &args[1];

    let img = match bmp::open(filename) {
        Ok(img) => img,
        Err(e) => { 
            eprintln!("Error opening BMP file '{}': {}", filename, e);
            process::exit(1);
        }
    };

    println!(
        "Image dimensions: {}x{}",
        img.get_width(),
        img.get_height()
    );
    println!("Extracting LSB data...");

    match extract_lsb(&img) {
        Ok(bytes) => {
            println!("Extracted {} bytes.", bytes.len());
            println!("Raw bytes as hex:");
            for byte in &bytes {
                print!("{:02x} ", byte);
            }
            println!();

            match String::from_utf8(bytes.clone()) {
                Ok(message) => {
                    if let Some(null_pos) = message.find('\0') {
                         println!("Decoded message (UTF-8, up to null terminator):");
                         println!("{}", &message[..null_pos]);
                    } else {
                         println!("Decoded message (UTF-8):");
                         println!("{}", message);
                         println!("\n(Note: Message might contain trailing non-printable data if not null-terminated)");
                    }
                }
                Err(e) => {
                    eprintln!("Could not decode extracted bytes as UTF-8: {}", e);
                    eprintln!("Printing raw bytes as hex:");
                    for (i, byte) in bytes.iter().enumerate() {
                        print!("{:02x} ", byte);
                        if (i + 1) % 16 == 0 {
                            println!();
                        }
                    }
                    println!();
                }
            }
        }
        Err(e) => {
            eprintln!("An unexpected IO error occurred during extraction: {}", e);
            process::exit(1);
        }
    }
}

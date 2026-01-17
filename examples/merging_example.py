"""
VTT merging example.

Demonstrates merging multiple VTT files with deduplication.
"""

from vttkit import VTTMerger

def main():
    # Initialize merger
    merger = VTTMerger()
    
    # Add multiple VTT files
    print("Merging VTT files...")
    
    files = ["part1.vtt", "part2.vtt", "part3.vtt"]
    
    for vtt_file in files:
        try:
            count = merger.add_from_file(vtt_file)
            print(f"Added {count} unique cues from {vtt_file}")
        except FileNotFoundError:
            print(f"File not found: {vtt_file}")
    
    # Save merged result
    output_file = "merged.vtt"
    merger.save(output_file)
    
    print(f"\nTotal cues in merged file: {merger.get_cue_count()}")
    print(f"Saved to: {output_file}")

if __name__ == "__main__":
    main()

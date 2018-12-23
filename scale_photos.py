
import os
from PIL import Image

# get color definition from any source, e.g., http://www.discoveryplayground.com/computer-programming-for-kids/rgb-colors/
COLOR_WHITE = 0xffffff

def half_adjust(total_length, image_length):
    return int((total_length - image_length) / 2.0)

def process_icon(filename, in_folder, out_folder, horizontal_size, vertical_size,
                 horizontal_margin, vertical_margin, background_color):
    output_image = Image.new('RGBA', (horizontal_size, vertical_size), color=background_color)

    icon_image = Image.open(os.path.join(in_folder, filename))
    image_width = icon_image.width
    image_height = icon_image.height

    effective_width = horizontal_size - horizontal_margin
    effective_height = vertical_size - vertical_margin

    scaling_x = float(effective_width) / float(image_width)
    scaling_y = float(effective_height) / float(image_height)

    # larger absolute magnitude determines which direction should be effective scaling
    effective_scaling = min( scaling_x, scaling_y)

    new_width = int(image_width*effective_scaling)
    new_height = int(image_height*effective_scaling)

    scaled_image = icon_image.resize((new_width, new_height), Image.ANTIALIAS)

    offset_x = half_adjust(horizontal_size, new_width)
    offset_y = half_adjust(vertical_size, new_height)

    output_image.paste(scaled_image, (offset_x, offset_y))

    output_filename = os.path.join(out_folder, filename)
    output_image.save(output_filename)

if __name__ == '__main__':
    try:
        import argparse

        argparser = argparse.ArgumentParser()
        argparser.add_argument("in_icons_folder_path", help="Input icons folder path")
        argparser.add_argument("out_icons_folder_path", help="Output icons folder path")
        argparser.add_argument("target_horizontal_size", help="Target horizontal size")
        argparser.add_argument("target_vertical_size", help="target_vertical size")

        argparser.add_argument("--horizontal_margin", help="Horizontal margin (pixels)", default=0)
        argparser.add_argument("--vertical_margin", help="Vertical margin (pixels)", default=0)

        argparser.add_argument("--background_color", help="Background color", default='white')

        args = argparser.parse_args()
    except ImportError:
        args = None


    in_folder = args.in_icons_folder_path
    out_folder = args.out_icons_folder_path
    if in_folder == out_folder:
        raise Exception("Input and output folders can't be the same")

    vertical_size = int(args.target_vertical_size)
    horizontal_size = int(args.target_horizontal_size)
    vertical_margin = int(args.vertical_margin)
    horizontal_margin = int(args.horizontal_margin)
    background_color = args.background_color

    for filename in os.listdir(in_folder):
        process_icon(filename, in_folder, out_folder, horizontal_size, vertical_size,
                     horizontal_margin, vertical_margin, background_color)

import argparse
import json

from drawscaffold.calculate import material_calculator2D
from drawscaffold.calculator.price_calculator import calculate_price
from drawscaffold.drawer import two_d_drawer

parser = argparse.ArgumentParser(description='Draw scaffolds professionally')
parser.add_argument("--verbose", action="store_true", help="gives outputs for debug")
parser.add_argument("--height-in-cm", type=float, required=True, help="construct height in centimeter")
parser.add_argument("--width-in-cm", type=float, required=True, help="construct width in centimeter")
parser.add_argument("--surface-slope", type=float, required=True, help="surface slope")
parser.add_argument("--toe-board-text", type=str, help="the text on toe board")
parser.add_argument("--start-with-right-diagonal", action="store_true", help="the first diagonal will be left bottom to right up")
parser.add_argument("--draw-surface-line", action="store_true", help="surface line on the drawing")
parser.add_argument("--biggest-surface-line", action="store_true", help="draws a line from the highest point where the structure and surface touch")

pattern_group = parser.add_mutually_exclusive_group()
pattern_group.add_argument("--use-x-pattern", action="store_true", help="force to use X pattern for diagonals")
pattern_group.add_argument("--use-zigzag-pattern", action="store_true", help="force to use ZigZag pattern for diagonals")
pattern_group.add_argument("--best-pattern", action="store_true", help="choose best pattern for diagonals")

parser.add_argument("--image", action="store_true", help="get the drawing and image of it")
parser.add_argument("--svg", action="store_true", help="get the drawing and svg of it")
parser.add_argument("--dxf", action="store_true", help="get the drawing and dxf of it")

parser.add_argument("--calculate", action="store_true", help="calculate the material count for the scaffold")
parser.add_argument("--calculate-price", action="store_true", help="calculate the material rent price for scaffold")
parser.add_argument("--side-count", type=int, default=1, help="how many sides will use for scaffold")

parser.add_argument("--project-name", type=str, default="scaffAI", help="project name that settings up to file name")

args = parser.parse_args()

if not args.use_x_pattern and not args.use_zigzag_pattern:
    args.best_pattern = True

toeText = args.toe_board_text
if toeText:
    toeText = str(toeText)
    if toeText.strip()=="":
        toeText = None

if args.calculate:
    materials = material_calculator2D(verbose=args.verbose, h=args.height_in_cm, w=args.width_in_cm, slope=args.surface_slope,
                     toe_text=toeText, r_diagonal=args.start_with_right_diagonal,
                     use_x_pattern=args.use_x_pattern, use_zigzag_pattern=args.use_zigzag_pattern,
                     use_best_pattern=args.best_pattern, side_count=args.side_count)

    print(json.dumps({"materials": materials}))
elif args.calculate_price:
    materials = material_calculator2D(verbose=args.verbose, h=args.height_in_cm, w=args.width_in_cm,
                                      slope=args.surface_slope,
                                      toe_text=toeText, r_diagonal=args.start_with_right_diagonal,
                                      use_x_pattern=args.use_x_pattern, use_zigzag_pattern=args.use_zigzag_pattern,
                                      use_best_pattern=args.best_pattern, side_count=args.side_count)

    ans = calculate_price(materials)

    if type(ans) is not tuple:
        print(json.dumps({"data": ans}))
    else:
        price, currency, symbol = ans
        print(json.dumps({"price": price, "currency": currency, "symbol": symbol}))
else:
    paths = two_d_drawer(verbose=args.verbose, h=args.height_in_cm, w=args.width_in_cm, slope=args.surface_slope,
                     toe_text=toeText, r_diagonal=args.start_with_right_diagonal, surface_line=args.draw_surface_line,
                     biggest_surface_line=args.biggest_surface_line, use_x_pattern=args.use_x_pattern, use_zigzag_pattern=args.use_zigzag_pattern,
                     use_best_pattern=args.best_pattern, image=args.image, svg=args.svg, dxf=args.dxf, project_name=args.project_name)
    print(json.dumps({"paths": paths}))

def bresenham_circle(arr_dims: (int, int) = (3, 3), r: int = 1) -> list:
    """ draw circle based on Bresenham's method """

    mask = [[0] * arr_dims[1] for _ in range(arr_dims[0])]
    xc, yc = arr_dims[1]//2, arr_dims[0]//2

    d = 3 - 2*r
    x = 0
    y = r
    mask = draw_circle(mask, xc, yc, x, y)

    while y >= x:

        # for each pixel we will draw all eight pixels
        x += 1

        # check for decision parameter and correspondingly update d, x, y
        if d > 0:
            y -= 1
            d = d + 4 * (x - y) + 10
        else:
            d = d + 4 * x + 6
        mask = draw_circle(mask, xc, yc, x, y)

    return mask


def draw_circle(mask: list = None, xc: int = 0, yc: int = 0, x: int = 0, y: int = 0):

    mask[xc+x][yc+y] = 1
    mask[xc-x][yc+y] = 1
    mask[xc+x][yc-y] = 1
    mask[xc-x][yc-y] = 1
    mask[xc+y][yc+x] = 1
    mask[xc-y][yc+x] = 1
    mask[xc+y][yc-x] = 1
    mask[xc-y][yc-x] = 1

    return mask

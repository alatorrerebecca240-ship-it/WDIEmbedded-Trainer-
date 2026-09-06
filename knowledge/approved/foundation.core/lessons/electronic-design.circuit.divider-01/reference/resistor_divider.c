#include "resistor_divider.h"

double divider_output(double vin, double top_ohms, double bottom_ohms)
{
    if (top_ohms < 0.0 || bottom_ohms < 0.0 || top_ohms + bottom_ohms <= 0.0) {
        return 0.0;
    }
    return vin * (bottom_ohms / (top_ohms + bottom_ohms));
}

# gen_konvoi.py
# membuat file gerak konvoi untuk TurtleMobility (INET)
NUM_CARS = 12
SPACING = 100
X_REAR = 200
Y_ROAD = 150
VARIATION = 0.20
CHANGE_EVERY = 5

for kmh in (40, 100):
    v = kmh / 3.6
    lo, hi = v * (1 - VARIATION), v * (1 + VARIATION)

    lines = ['<movements>']
    for i in range(NUM_CARS):
        x = X_REAR + (NUM_CARS - 1 - i) * SPACING
        lines += [
            f'  <movement id="{i}">',
            f'      <set x="{x}" y="{Y_ROAD}" angle="0" borderPolicy="reflect"/>',
            f'      <repeat>',
            f'          <set speed="uniform({lo:.3f}, {hi:.3f})"/>',
            f'          <forward t="{CHANGE_EVERY}"/>',
            f'      </repeat>',
            f'  </movement>',
        ]
    lines.append('</movements>')

    with open(f'konvoi{kmh}.xml', 'w') as f:
        f.write('\n'.join(lines))
    print(f'konvoi{kmh}.xml dibuat: {lo:.2f}-{hi:.2f} m/s')
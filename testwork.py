l = {
    'hw': [{'test': 'wkaka',
    'lals': 'dfdfg', 'symbol': 'jajaj'}, {'test': 'grisha',
    'lals': 'asasas', 'symbol': 'jajaja'}],
    'lol': 'wjeje'
}
new_dict = {}
for i in l:
    print(i)
hw = l.get('hw')
print(hw)
for i in hw:
    test = i.get('test')
    lals = i.get('lals')
    symbol = i.get('symbol')
print(test, lals)

new_dict[symbol] = {'test': test, 'lals': lals}
print(new_dict)

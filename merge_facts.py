import yaml

# Читаем все файлы периодов
periods_data = []

for i in range(1, 8):
    with open(f'facts/facts_period_{i}.yaml', 'r', encoding='utf-8') as f:
        period_data = yaml.safe_load(f)
        periods_data.append(period_data)

# Создаём объединённую структуру
all_facts = {'periods': periods_data}

# Записываем в all_facts.yaml
with open('facts/all_facts.yaml', 'w', encoding='utf-8') as f:
    yaml.dump(all_facts, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

print("Merged all 7 periods into facts/all_facts.yaml")
print(f"Total facts: {sum(len(p['facts']) for p in periods_data)}")

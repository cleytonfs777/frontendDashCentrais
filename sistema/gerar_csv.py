import csv
import random
from datetime import datetime, timedelta

random.seed(42)

cobs = [11, 21, 22, 31, 32, 4, 51, 52, 61]
filas = ['Emergência 193', 'Atendimento Geral', 'Resgate', 'Incêndio', 'Defesa Civil', 'Salvamento', 'Informações']

atendentes_por_cob = {
    11: ['Ana Silva', 'Carlos Souza', 'Maria Oliveira', 'João Santos'],
    21: ['Pedro Lima', 'Fernanda Costa', 'Lucas Almeida', 'Juliana Martins'],
    22: ['Roberto Dias', 'Camila Rocha', 'Felipe Araújo'],
    31: ['Amanda Pereira', 'Bruno Ferreira', 'Daniela Gomes', 'Eduardo Ribeiro'],
    32: ['Gustavo Mendes', 'Helena Barbosa', 'Igor Carvalho'],
    4: ['Larissa Nunes', 'Marcos Vieira', 'Natália Correia', 'Oscar Teixeira', 'Paula Monteiro'],
    51: ['Ricardo Castro', 'Sandra Pinto', 'Thiago Moura'],
    52: ['Vanessa Lopes', 'Wagner Cardoso', 'Yasmin Freitas'],
    61: ['André Campos', 'Bianca Duarte', 'Cláudio Ramos', 'Diana Fonseca']
}

rows = []
start_date = datetime(2026, 1, 1)
end_date = datetime(2026, 2, 28)
current = start_date

while current <= end_date:
    is_weekday = current.weekday() < 5
    base_calls = random.randint(80, 150) if is_weekday else random.randint(40, 90)

    for _ in range(base_calls):
        cob = random.choice(cobs)
        hour_weights = [1, 1, 1, 1, 1, 1, 3, 5, 8, 10, 10, 9, 8, 7, 8, 9, 8, 6, 4, 3, 2, 2, 1, 1]
        hour = random.choices(range(24), weights=hour_weights, k=1)[0]
        minute = random.randint(0, 59)
        second = random.randint(0, 59)
        hora = f'{hour:02d}:{minute:02d}:{second:02d}'

        estado = 1 if random.random() < 0.70 else 0

        if estado == 1:
            duracao = random.choice([
                random.randint(10, 60),
                random.randint(60, 300),
                random.randint(300, 900),
                random.randint(900, 1800)
            ])
        else:
            duracao = random.randint(0, 15)

        fila = random.choice(filas)
        teleatendente = random.choice(atendentes_por_cob[cob]) if estado == 1 else ''

        rows.append({
            'data': current.strftime('%Y-%m-%d'),
            'hora': hora,
            'duracao': duracao,
            'fila': fila,
            'teleatendente': teleatendente,
            'estado': estado,
            'cob': cob
        })

    current += timedelta(days=1)

random.shuffle(rows)

with open('data/geral_df.csv', 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['data', 'hora', 'duracao', 'fila', 'teleatendente', 'estado', 'cob'])
    writer.writeheader()
    writer.writerows(rows)

print(f'CSV gerado com {len(rows)} registros')
print(f'Período: {start_date.strftime("%Y-%m-%d")} a {end_date.strftime("%Y-%m-%d")}')
print(f'COBs: {sorted(set(r["cob"] for r in rows))}')

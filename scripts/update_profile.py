"""Refresh public projects and contribution statistics with GitHub's APIs."""
import base64
import datetime as dt
import html
import json
import os
from pathlib import Path
import re
import textwrap
import urllib.request
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
OWNER = os.environ.get('PROFILE_OWNER', 'allancorreaz')
TOKEN = os.environ.get('GH_TOKEN', '')
START, END = '<!-- PROJECTS:START -->', '<!-- PROJECTS:END -->'
KNOWN = {
 'Nexora-AI': ('Nexora AI', 'Assistente local em desenvolvimento com Next.js, FastAPI e Ollama. Chat com histórico no navegador, respostas em Markdown, prévia de documentos e testes de API; recuperação documental com RAG planejada.'),
 'Gestao-de-Implantacao': ('Centro de Controle da Implantação', 'Portal de acompanhamento de implantação de ERP, com tarefas, tickets, pendências, perfis de acesso, auditoria e exportação de relatórios.'),
 'AprovadosQuestoes': ('Aprovados Questões', 'Plataforma de estudos com filtros, simulados, cronômetro, autenticação e biblioteca de materiais públicos, integrada ao Cloudflare D1.'),
 'registro-operacional': ('Registro Operacional', 'Aplicação para operações portuárias com continuidade entre turnos, cálculo de indicadores, persistência de dados e relatórios em PDF.'),
 'apriscourbano': ('Aprisco Urbano', 'Site institucional com área administrativa para conteúdo, usuários, permissões e auditoria.'),
 'vendas-e-estoque': ('Controle de Vendas e Estoque', 'Aplicação com Next.js, TypeScript e Prisma para cadastro de produtos e clientes, registro de vendas e atualização de estoque.'),
 'santscompany': ('Sants Company', 'Site institucional com portfólio, blog e formulário integrado à API Resend, com validação no servidor e mecanismos anti-spam.'),
 'financeiro-app': ('Financeiro App', 'Back-end em desenvolvimento com FastAPI e integração à Pluggy para sincronização financeira via Open Finance e webhooks.'),
 'barbershop-management-system': ('Gestão de Barbearia', 'Aplicação Django com gestão de clientes, serviços, atendimentos, estoque e movimentações de caixa.'),
 'Portif-lio': ('Portfólio pessoal', 'Apresentação profissional e seleção de projetos de desenvolvimento web.'),
 'fsw-barber': ('FSW Barber — Em desenvolvimento', 'Projeto de estudo em desenvolvimento para uma aplicação de barbearia com Next.js e Prisma.'),
 'FWS-BarberShopService': ('FWS BarberShop Service — Em desenvolvimento', 'Projeto de barbearia em desenvolvimento. Documentação técnica em preparação.'),
}
FEATURED = ['Nexora-AI', 'Gestao-de-Implantacao', 'AprovadosQuestoes', 'registro-operacional', 'apriscourbano', 'vendas-e-estoque']

def api(path, payload=None, accept='application/vnd.github+json'):
    url = path if path.startswith('https://') else 'https://api.github.com' + path
    headers = {'Accept': accept, 'User-Agent': 'allan-profile-updater', 'X-GitHub-Api-Version': '2022-11-28'}
    if TOKEN:
        headers['Authorization'] = 'Bearer ' + TOKEN
    req = urllib.request.Request(url, data=json.dumps(payload).encode() if payload else None, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)

def repositories():
    result = []
    for page in range(1, 101):
        batch = api(f'/users/{OWNER}/repos?type=owner&sort=updated&per_page=100&page={page}')
        result.extend(batch)
        if len(batch) < 100:
            break
    return [r for r in result if not r.get('private') and not r.get('fork') and r['name'].lower() != OWNER.lower() and r.get('size', 0) > 0]

def plain(value):
    value = html.unescape(str(value or ''))
    return ' '.join(re.sub(r'<[^>]*>', '', value).split())[:350]

def description(repo):
    name = repo['name']
    if repo.get('description'):
        return plain(repo['description'])
    if name in KNOWN:
        return KNOWN[name][1]
    try:
        data = api(f'/repos/{OWNER}/{quote(name)}/readme')
        text = base64.b64decode(data['content']).decode('utf-8')
        for block in re.split(r'\n\s*\n', text):
            block = block.strip()
            if not block or block.startswith(('#', '!', '[!', '<', '```', '|', '-', '>')):
                continue
            if 'create-next-app' in block or 'This is a [Next.js]' in block:
                continue
            return plain(re.sub(r'\[([^]]+)\]\([^)]+\)', r'\1', block).replace('*', ''))
    except (OSError, ValueError, KeyError, UnicodeError):
        pass
    language = repo.get('language')
    return f'Projeto em {language}. Consulte o repositório para acompanhar o desenvolvimento.' if language else 'Consulte o repositório para acompanhar o desenvolvimento.'

def project_preview(repo, title):
    """Generate a repository cover locally, without external image services."""
    folder = ROOT / 'profile' / 'projects'
    folder.mkdir(parents=True, exist_ok=True)
    title_lines = textwrap.wrap(title, width=42)[:2]
    summary = textwrap.wrap(description(repo), width=92)[:2]
    content = ['<svg xmlns="http://www.w3.org/2000/svg" width="900" height="260" viewBox="0 0 900 260" role="img">', f'<title>{html.escape(title)}</title>', '<rect x="1" y="1" width="898" height="258" rx="12" fill="#ffffff" stroke="#d0d7de"/>', '<rect x="1" y="1" width="7" height="258" rx="3" fill="#238636"/>', '<g font-family="Arial,sans-serif" fill="#1f2328">', '<text x="30" y="35" font-size="12" fill="#59636e">PROJETO · ALLAN DE MELO CORREA</text>']
    for i, line in enumerate(title_lines):
        content.append(f'<text x="30" y="{78+i*34}" font-size="28" font-weight="700">{html.escape(line)}</text>')
    for i, line in enumerate(summary):
        content.append(f'<text x="30" y="{153+i*23}" font-size="15" fill="#59636e">{html.escape(line)}</text>')
    language = repo.get('language') or 'Código e documentação'
    content += [f'<text x="30" y="230" font-size="13">{html.escape(language)} · github.com/{OWNER}/{html.escape(repo["name"])}</text>', '</g></svg>']
    (folder / (repo['name'] + '.svg')).write_text('\n'.join(content))

def card(repo):
    name = repo['name']
    title = KNOWN.get(name, (name.replace('-', ' '), ''))[0]
    url = repo['html_url']
    image = f'./profile/projects/{quote(name)}.svg'
    project_preview(repo, title)
    state = ' · Arquivado' if repo.get('archived') else ''
    language = (' · ' + repo['language']) if repo.get('language') else ''
    return f'''<a href="{html.escape(url, quote=True)}"><img src="{image}" alt="Prévia do repositório {html.escape(title, quote=True)}" width="440" /></a>\n\n**[{title}]({url})**{language}{state}\n\n{html.escape(description(repo))}\n'''

def projects(repos):
    lookup = {r['name']: r for r in repos}
    featured = [lookup[n] for n in FEATURED if n in lookup]
    other = sorted((r for r in repos if r['name'] not in FEATURED), key=lambda r: r.get('pushed_at') or '', reverse=True)
    sections = ['As imagens são prévias dos repositórios; demonstrações estão nos respectivos projetos.\n']
    sections += [card(r) for r in featured]
    if other:
        sections += ['<details>\n<summary>Outros projetos e estudos</summary>\n']
        sections += [card(r) for r in other]
        sections += ['</details>\n']
    sections += [f'[Todos os repositórios](https://github.com/{OWNER}?tab=repositories)\n', 'Atualização automática a cada hora. Novos repositórios públicos próprios aparecem nesta seção; forks, repositórios vazios e privados ficam de fora.\n']
    return '\n'.join(sections)

def update_projects(repos):
    path = ROOT / 'README.md'
    text = path.read_text()
    if text.count(START) != 1 or text.count(END) != 1:
        raise ValueError('README precisa conter exatamente um par de marcadores PROJECTS.')
    before, tail = text.split(START)
    _, after = tail.split(END)
    path.write_text(before + START + '\n\n' + projects(repos) + '\n' + END + after)

def streaks(days):
    best = run = 0
    for day in days:
        run = run + 1 if day['contributionCount'] else 0
        best = max(best, run)
    active = days[:-1] if days and not days[-1]['contributionCount'] else days
    current = 0
    for day in reversed(active):
        if not day['contributionCount']:
            break
        current += 1
    return current, best

def statistics(repos):
    query = '''query($login:String!){user(login:$login){followers{totalCount} contributionsCollection{totalCommitContributions totalPullRequestContributions totalIssueContributions contributionCalendar{totalContributions weeks{contributionDays{date contributionCount color}}}}}}'''
    result = api('/graphql', {'query': query, 'variables': {'login': OWNER}})
    if result.get('errors'):
        raise RuntimeError('GitHub GraphQL: ' + json.dumps(result['errors']))
    user = result['data']['user']
    collection = user['contributionsCollection']
    calendar = collection['contributionCalendar']
    weeks = calendar['weeks']
    days = [day for week in weeks for day in week['contributionDays']]
    current, best = streaks(days)
    stars = sum(r.get('stargazers_count', 0) for r in repos)
    values = [('Contribuições', calendar['totalContributions']), ('Commits elegíveis', collection['totalCommitContributions']), ('Sequência atual', f'{current} dias'), ('Maior sequência', f'{best} dias'), ('Repos. públicos próprios', len(repos)), ('Estrelas', stars), ('Seguidores', user['followers']['totalCount'])]
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="900" height="370" viewBox="0 0 900 370" role="img" aria-labelledby="title desc">', '<title id="title">Atividade de Allan de Melo Correa no GitHub</title>', '<desc id="desc">Contribuições e commits elegíveis dos últimos 12 meses. Sequências medidas nesta janela; repositórios, estrelas e seguidores são totais atuais públicos.</desc>', '<rect width="899" height="369" x=".5" y=".5" rx="12" fill="#ffffff" stroke="#d0d7de"/>', '<g font-family="Arial,sans-serif" fill="#1f2328">', '<text x="28" y="36" font-size="20" font-weight="700">Atividade no GitHub</text>', '<text x="28" y="60" font-size="12" fill="#59636e">Contribuições e sequências nos últimos 12 meses · Dados da API do GitHub</text>']
    for i, (label, value) in enumerate(values):
        x, y = 28 + (i % 4) * 215, 96 + (i // 4) * 65
        svg += [f'<text x="{x}" y="{y}" font-size="11" fill="#59636e">{label}</text>', f'<text x="{x}" y="{y+27}" font-size="24" font-weight="700">{value}</text>']
    for col, week in enumerate(weeks):
        for day in week['contributionDays']:
            row = (dt.date.fromisoformat(day['date']).weekday() + 1) % 7
            color = day['color'] if re.fullmatch(r'#[0-9a-fA-F]{6}', day['color']) else '#ebedf0'
            svg.append(f'<rect x="{28+col*16}" y="{220+row*15}" width="12" height="12" rx="2" fill="{color}"><title>{day["date"]}: {day["contributionCount"]} contribuições</title></rect>')
    stamp = dt.datetime.now(dt.timezone.utc).strftime('%d/%m/%Y %H:%M UTC')
    svg += [f'<text x="28" y="349" font-size="11" fill="#59636e">Atualizado em {stamp} · O GitHub pode levar até 24 h para contabilizar contribuições.</text>', '</g></svg>']
    dest = ROOT / 'profile'
    dest.mkdir(exist_ok=True)
    (dest / 'activity.svg').write_text('\n'.join(svg))

def main():
    repos = repositories()
    # Fetch statistics first: an API error must not silently publish zero counters.
    statistics(repos)
    update_projects(repos)
    print(f'Perfil atualizado: {len(repos)} repositórios públicos próprios.')

if __name__ == '__main__':
    main()

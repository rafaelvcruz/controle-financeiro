import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { FormsModule } from '@angular/forms';

type Category = { id: number; name: string; nature: string; suggested_percentage: string | null; active: boolean };

@Component({ selector: 'app-root', standalone: true, imports: [CommonModule, FormsModule], template: `
<div class="shell">
  <aside class="sidebar">
    <div class="brand"><span class="brand-mark">$</span><div><strong>Meu Financeiro</strong><small>CONTROLE FAMILIAR</small></div></div>
    <nav><a class="active">▦ <span>Visão geral</span></a><a>⇄ <span>Lançamentos</span></a><a>▤ <span>Planejamento</span></a><a>▣ <span>Cartões</span></a><a>◷ <span>Relatórios</span></a><a>⚙ <span>Cadastros</span></a></nav>
    <div class="sidebar-foot">Versão inicial · 0.1.0</div>
  </aside>
  <main class="content">
    <header><div><p class="eyebrow">CONTROLE FINANCEIRO FAMILIAR</p><h1>Visão geral</h1><p class="muted">Sua organização financeira em um só lugar.</p></div><div class="avatar">RF</div></header>
    <section class="notice"><strong>Ambiente inicial</strong><span>Cadastre pessoas, contas e categorias antes de registrar movimentações. Nenhum saldo ou lançamento foi presumido.</span></section>
    <section class="cards">
      <article class="metric"><span>Saldo consolidado</span><strong>—</strong><small>Será calculado após cadastrar as contas</small></article>
      <article class="metric"><span>Receitas do mês</span><strong>—</strong><small>Aguardando lançamentos</small></article>
      <article class="metric"><span>Despesas do mês</span><strong>—</strong><small>Aguardando lançamentos</small></article>
      <article class="metric"><span>Resultado do mês</span><strong>—</strong><small>Aguardando lançamentos</small></article>
    </section>
    <section class="panel">
      <div class="panel-head"><div><h2>Cadastro de categorias</h2><p class="muted">Base para classificar receitas e despesas.</p></div><span class="count">{{ categories.length }} cadastradas</span></div>
      <form (ngSubmit)="addCategory()" class="category-form"><input name="categoryName" [(ngModel)]="newCategory" placeholder="Nome da categoria" required minlength="2"><select name="nature" [(ngModel)]="newNature"><option value="MISTA">Mista</option><option value="RECEITA">Receita</option><option value="DESPESA">Despesa</option><option value="INVESTIMENTO">Investimento</option></select><button [disabled]="saving || !newCategory.trim()">{{ saving ? 'Salvando…' : 'Adicionar' }}</button></form>
      <p class="feedback" *ngIf="message">{{ message }}</p>
      <div class="table-wrap"><table><thead><tr><th>Categoria</th><th>Natureza</th><th>Status</th></tr></thead><tbody><tr *ngFor="let c of categories"><td>{{ c.name }}</td><td>{{ c.nature }}</td><td><span class="status">{{ c.active ? 'Ativa' : 'Inativa' }}</span></td></tr><tr *ngIf="!categories.length"><td colspan="3" class="empty">Nenhuma categoria cadastrada.</td></tr></tbody></table></div>
    </section>
    <footer>Dados armazenados no servidor local · API FastAPI</footer>
  </main>
</div>
` })
export class AppComponent implements OnInit {
  private http = inject(HttpClient);
  categories: Category[] = [];
  newCategory = '';
  newNature = 'MISTA';
  saving = false;
  message = '';
  ngOnInit() { this.loadCategories(); }
  loadCategories() { this.http.get<Category[]>('/api/categories').subscribe({ next: data => this.categories = data, error: () => this.message = 'Não foi possível carregar as categorias. Verifique se a API está ativa.' }); }
  addCategory() {
    if (!this.newCategory.trim()) return;
    this.saving = true; this.message = '';
    this.http.post<Category>('/api/categories', { name: this.newCategory.trim(), nature: this.newNature, active: true }).subscribe({
      next: item => { this.categories = [...this.categories, item]; this.newCategory = ''; this.message = 'Categoria cadastrada.'; this.saving = false; },
      error: err => { this.message = err.status === 409 ? 'Já existe uma categoria com esse nome.' : 'Falha ao cadastrar. Confira a API.'; this.saving = false; }
    });
  }
}

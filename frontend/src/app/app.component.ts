import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { FormsModule } from '@angular/forms';

type Category = { id: number; name: string; nature: string; active: boolean };
type Group = { id: number; category_id: number; name: string; active: boolean };
type Subgroup = { id: number; group_id: number; name: string; active: boolean };
type Person = { id: number; name: string; active: boolean };
type Account = { id: number; name: string; account_type: string; initial_balance: string; balance_date: string; active: boolean };
type Entry = { id: number; movement_date: string; competence_date: string; entry_type: string; description: string; amount: string; person_id: number | null; account_id: number; subgroup_id: number | null; status: string };

const today = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`; };

@Component({ selector: 'app-root', standalone: true, imports: [CommonModule, FormsModule], template: `
<div class="shell">
  <aside class="sidebar">
    <div class="brand"><span class="brand-mark">$</span><div><strong>Meu Financeiro</strong><small>CONTROLE FAMILIAR</small></div></div>
    <nav><a class="active">⇄ <span>Lançamentos</span></a><a>▦ <span>Visão geral</span></a><a>▤ <span>Planejamento</span></a><a>▣ <span>Cartões</span></a><a>◷ <span>Relatórios</span></a><a>⚙ <span>Cadastros</span></a></nav>
    <div class="sidebar-foot">Versão inicial · 0.2.0</div>
  </aside>
  <main class="content">
    <header><div><p class="eyebrow">CONTROLE FINANCEIRO FAMILIAR</p><h1>Lançamentos</h1><p class="muted">Registre e acompanhe as movimentações da família.</p></div><div class="avatar">RF</div></header>
    <section class="notice"><strong>Como os saldos são calculados</strong><span>Somente lançamentos realizados afetam os saldos. Itens previstos ficam fora do saldo atual, cancelados são ignorados e transferências entre contas não são tratadas como receita ou despesa.</span></section>
    <section class="panel entry-panel">
      <div class="panel-head"><div><h2>Novo lançamento</h2><p class="muted">Informe os dados da receita, despesa ou investimento.</p></div></div>
      <form (ngSubmit)="addEntry()" class="entry-form">
        <label>Tipo<select name="entryType" [(ngModel)]="form.entry_type" (ngModelChange)="onTypeChange()"><option value="DESPESA">Despesa</option><option value="RECEITA">Receita</option><option value="INVESTIMENTO">Investimento</option></select></label>
        <label>Descrição<input name="description" [(ngModel)]="form.description" placeholder="Ex.: Supermercado" required minlength="2"></label>
        <label>Valor (R$)<input name="amount" type="number" min="0.01" step="0.01" [(ngModel)]="form.amount" placeholder="0,00" required></label>
        <label>Data<input name="movementDate" type="date" [(ngModel)]="form.movement_date" required></label>
        <label>Competência<input name="competenceDate" type="date" [(ngModel)]="form.competence_date" required></label>
        <label>Conta<select name="account" [(ngModel)]="form.account_id" required><option [ngValue]="null">Selecione</option><option *ngFor="let a of accounts" [ngValue]="a.id">{{ a.name }}</option></select></label>
        <label>Responsável<select name="person" [(ngModel)]="form.person_id"><option [ngValue]="null">Não informado</option><option *ngFor="let p of people" [ngValue]="p.id">{{ p.name }}</option></select></label>
        <label>Categoria<select name="category" [(ngModel)]="selectedCategoryId" (ngModelChange)="onCategoryChange()"><option [ngValue]="null">Selecione</option><option *ngFor="let c of availableCategories" [ngValue]="c.id">{{ c.name }}</option></select></label>
        <label>Grupo<select name="group" [(ngModel)]="selectedGroupId" (ngModelChange)="onGroupChange()"><option [ngValue]="null">Selecione</option><option *ngFor="let g of availableGroups" [ngValue]="g.id">{{ g.name }}</option></select></label>
        <label>Subgrupo<select name="subgroup" [(ngModel)]="form.subgroup_id"><option [ngValue]="null">Não informado</option><option *ngFor="let s of availableSubgroups" [ngValue]="s.id">{{ s.name }}</option></select></label>
        <label>Status<select name="status" [(ngModel)]="form.status"><option value="REALIZADO">Realizado</option><option value="PREVISTO">Previsto</option></select></label>
        <div class="form-actions"><button [disabled]="saving || !canSave">{{ saving ? 'Salvando…' : 'Salvar lançamento' }}</button></div>
      </form>
      <p class="feedback" *ngIf="message">{{ message }}</p>
      <p class="helper" *ngIf="!accounts.length">Cadastre pelo menos uma conta financeira antes de registrar lançamentos.</p>
    </section>
    <section class="panel list-panel">
      <div class="panel-head"><div><h2>Movimentações recentes</h2><p class="muted">Lançamentos cadastrados, do mais recente para o mais antigo.</p></div><span class="count">{{ entries.length }} registros</span></div>
      <div class="table-wrap"><table><thead><tr><th>Data</th><th>Descrição</th><th>Tipo</th><th>Conta</th><th>Status</th><th class="right">Valor</th><th></th></tr></thead><tbody>
        <tr *ngFor="let e of entries"><td>{{ e.movement_date | date:'dd/MM/yyyy':'UTC' }}</td><td>{{ e.description }}</td><td>{{ typeLabel(e.entry_type) }}</td><td>{{ accountName(e.account_id) }}</td><td><span class="status" [class.pending]="e.status === 'PREVISTO'">{{ e.status === 'PREVISTO' ? 'Previsto' : e.status === 'CANCELADO' ? 'Cancelado' : 'Realizado' }}</span></td><td class="right" [class.income]="e.entry_type === 'RECEITA'">{{ e.amount | currency:'BRL':'symbol':'1.2-2':'pt-BR' }}</td><td><button class="link-button" *ngIf="e.status !== 'CANCELADO'" (click)="cancelEntry(e)">Cancelar</button></td></tr>
        <tr *ngIf="!entries.length"><td colspan="7" class="empty">Nenhum lançamento cadastrado.</td></tr>
      </tbody></table></div>
    </section>
    <footer>Dados armazenados no servidor local · API FastAPI</footer>
  </main>
</div>
` })
export class AppComponent implements OnInit {
  private http = inject(HttpClient);
  categories: Category[] = []; groups: Group[] = []; subgroups: Subgroup[] = []; people: Person[] = []; accounts: Account[] = []; entries: Entry[] = [];
  selectedCategoryId: number | null = null; selectedGroupId: number | null = null;
  saving = false; message = '';
  form = { movement_date: today(), competence_date: today(), entry_type: 'DESPESA', description: '', amount: null as number | null, person_id: null as number | null, account_id: null as number | null, subgroup_id: null as number | null, status: 'REALIZADO' };
  get availableCategories() { return this.categories.filter(c => c.active && (c.nature === 'MISTA' || c.nature === this.form.entry_type)); }
  get availableGroups() { return this.groups.filter(g => g.active && g.category_id === this.selectedCategoryId); }
  get availableSubgroups() { return this.subgroups.filter(s => s.active && s.group_id === this.selectedGroupId); }
  get canSave() { return !!this.form.description.trim() && !!this.form.amount && this.form.amount > 0 && !!this.form.account_id; }
  ngOnInit() { this.loadAll(); }
  onTypeChange() {
    if (!this.availableCategories.some(category => category.id === this.selectedCategoryId)) {
      this.selectedCategoryId = null;
      this.onCategoryChange();
    }
  }
  loadAll() {
    this.http.get<Category[]>('/api/categories').subscribe({next: v => this.categories = v, error: () => this.message = 'Não foi possível carregar categorias.'});
    this.http.get<Group[]>('/api/groups').subscribe({next: v => this.groups = v});
    this.http.get<Subgroup[]>('/api/subgroups').subscribe({next: v => this.subgroups = v});
    this.http.get<Person[]>('/api/people').subscribe({next: v => this.people = v});
    this.http.get<Account[]>('/api/accounts').subscribe({next: v => this.accounts = v, error: () => this.message = 'Não foi possível carregar contas.'});
    this.loadEntries();
  }
  loadEntries() { this.http.get<Entry[]>('/api/entries').subscribe({next: v => this.entries = v, error: () => this.message = 'Não foi possível carregar os lançamentos.'}); }
  onCategoryChange() { this.selectedGroupId = null; this.form.subgroup_id = null; }
  onGroupChange() { this.form.subgroup_id = null; }
  addEntry() {
    if (!this.canSave) return;
    this.saving = true; this.message = '';
    const payload = {...this.form, amount: Number(this.form.amount), subgroup_id: this.form.subgroup_id};
    this.http.post<Entry>('/api/entries', payload).subscribe({
      next: item => { this.entries = [item, ...this.entries]; this.form.description = ''; this.form.amount = null; this.selectedCategoryId = null; this.selectedGroupId = null; this.form.subgroup_id = null; this.message = 'Lançamento cadastrado com sucesso.'; this.saving = false; },
      error: err => { this.message = err.error?.detail || 'Falha ao cadastrar lançamento. Verifique os cadastros e tente novamente.'; this.saving = false; }
    });
  }
  cancelEntry(entry: Entry) {
    if (!confirm(`Cancelar o lançamento '${entry.description}'?`)) return;
    this.http.patch<Entry>(`/api/entries/${entry.id}/status`, {status: 'CANCELADO'}).subscribe({next: updated => { this.entries = this.entries.map(e => e.id === updated.id ? updated : e); this.message = 'Lançamento cancelado.'; }, error: () => this.message = 'Não foi possível cancelar o lançamento.'});
  }
  accountName(id: number) { return this.accounts.find(a => a.id === id)?.name || `Conta #${id}`; }
  typeLabel(type: string) { return type === 'RECEITA' ? 'Receita' : type === 'INVESTIMENTO' ? 'Investimento' : 'Despesa'; }
}

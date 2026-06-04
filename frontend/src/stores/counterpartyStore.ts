import { create } from 'zustand';
import { counterpartiesApi } from '@/api/client';
import type { Counterparty, CreateCounterpartyInput, ContactPersonInput, ContactPerson, CounterpartyCustomer, PaginatedResponse } from '@/types';

interface CounterpartyState {
  counterparties: Counterparty[];
  currentCounterparty: Counterparty | null;
  contactPerson: ContactPerson | null;
  customers: CounterpartyCustomer[];
  branches: Counterparty[];
  pagination: {
    page: number;
    size: number;
    total_items: number;
    total_pages: number;
    has_next: boolean;
    has_prev: boolean;
  };
  isLoading: boolean;
  error: string | null;
  
  fetchCounterparties: (page?: number, size?: number) => Promise<void>;
  fetchCounterparty: (id: string) => Promise<void>;
  createCounterparty: (data: CreateCounterpartyInput) => Promise<Counterparty>;
  updateCounterparty: (id: string, data: Partial<CreateCounterpartyInput>) => Promise<void>;
  deleteCounterparty: (id: string) => Promise<void>;
  fetchContactPerson: (id: string) => Promise<void>;
  updateContactPerson: (id: string, data: ContactPersonInput) => Promise<void>;
  fetchCustomers: (id: string) => Promise<void>;
  fetchBranches: (id: string) => Promise<void>;
  clearCurrent: () => void;
}

export const useCounterpartyStore = create<CounterpartyState>((set) => ({
  counterparties: [],
  currentCounterparty: null,
  contactPerson: null,
  customers: [],
  branches: [],
  pagination: {
    page: 1,
    size: 10,
    total_items: 0,
    total_pages: 0,
    has_next: false,
    has_prev: false,
  },
  isLoading: false,
  error: null,

  fetchCounterparties: async (page = 1, size = 10) => {
    set({ isLoading: true, error: null });
    try {
      const response: PaginatedResponse<Counterparty> = await counterpartiesApi.getAll(page, size);
      set({ 
        counterparties: response.items,
        pagination: {
          page: response.page,
          size: response.size,
          total_items: response.total_items,
          total_pages: response.total_pages,
          has_next: response.has_next,
          has_prev: response.has_prev,
        },
        isLoading: false 
      });
    } catch (error) {
      set({ error: 'Ошибка загрузки контрагентов', isLoading: false });
    }
  },

  fetchCounterparty: async (id: string) => {
    set({ isLoading: true, error: null });
    try {
      const counterparty = await counterpartiesApi.getById(id);
      set({ currentCounterparty: counterparty, isLoading: false });
    } catch (error) {
      set({ error: 'Ошибка загрузки контрагента', isLoading: false });
    }
  },

  createCounterparty: async (data: CreateCounterpartyInput) => {
    set({ isLoading: true, error: null });
    try {
      const counterparty = await counterpartiesApi.create(data);
      set(state => ({ 
        counterparties: [...state.counterparties, counterparty],
        isLoading: false 
      }));
      return counterparty;
    } catch (error) {
      set({ error: 'Ошибка создания контрагента', isLoading: false });
      throw error;
    }
  },

  updateCounterparty: async (id: string, data: Partial<CreateCounterpartyInput>) => {
    set({ isLoading: true, error: null });
    try {
      const updated = await counterpartiesApi.update(id, data);
      set(state => ({
        counterparties: state.counterparties.map(c => c.id === id ? updated : c),
        currentCounterparty: state.currentCounterparty?.id === id ? updated : state.currentCounterparty,
        isLoading: false
      }));
    } catch (error) {
      set({ error: 'Ошибка обновления контрагента', isLoading: false });
      throw error;
    }
  },

  deleteCounterparty: async (id: string) => {
    set({ isLoading: true, error: null });
    try {
      await counterpartiesApi.delete(id);
      set(state => ({
        counterparties: state.counterparties.filter(c => c.id !== id),
        isLoading: false
      }));
    } catch (error) {
      set({ error: 'Ошибка удаления контрагента', isLoading: false });
      throw error;
    }
  },

  fetchContactPerson: async (id: string) => {
    try {
      const contactPerson = await counterpartiesApi.getContactPerson(id);
      set({ contactPerson });
    } catch {
      set({ contactPerson: null });
    }
  },

  updateContactPerson: async (id: string, data: ContactPersonInput) => {
    set({ isLoading: true, error: null });
    try {
      const contactPerson = await counterpartiesApi.updateContactPerson(id, data);
      set({ contactPerson, isLoading: false });
    } catch (error) {
      set({ error: 'Ошибка обновления контактного лица', isLoading: false });
      throw error;
    }
  },

  fetchCustomers: async (id: string) => {
    try {
      const customers = await counterpartiesApi.getCustomers(id);
      set({ customers });
    } catch {
      set({ customers: [] });
    }
  },

  fetchBranches: async (id: string) => {
    try {
      const branches = await counterpartiesApi.getBranches(id);
      set({ branches });
    } catch {
      set({ branches: [] });
    }
  },

  clearCurrent: () => {
    set({ currentCounterparty: null, contactPerson: null, customers: [], branches: [] });
  },
}));

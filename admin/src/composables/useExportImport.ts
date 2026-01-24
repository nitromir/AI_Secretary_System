import { ref } from 'vue'
import { useToastStore } from '@/stores/toast'
import { useAuditStore } from '@/stores/audit'

export interface ExportData {
  version: string
  exportedAt: string
  type: 'full' | 'faq' | 'presets' | 'personas' | 'settings'
  data: any
}

export function useExportImport() {
  const toast = useToastStore()
  const audit = useAuditStore()
  const isExporting = ref(false)
  const isImporting = ref(false)

  function downloadJson(data: any, filename: string) {
    const json = JSON.stringify(data, null, 2)
    const blob = new Blob([json], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  async function exportFaq(): Promise<void> {
    isExporting.value = true
    try {
      const response = await fetch('/admin/faq')
      if (!response.ok) throw new Error('Failed to fetch FAQ')
      const faqData = await response.json()

      const exportData: ExportData = {
        version: '1.0',
        exportedAt: new Date().toISOString(),
        type: 'faq',
        data: faqData
      }

      downloadJson(exportData, `faq-export-${Date.now()}.json`)
      audit.log('export', 'faq', 'Exported FAQ data')
      toast.success('FAQ exported successfully')
    } catch (e) {
      toast.error('Export failed', (e as Error).message)
    } finally {
      isExporting.value = false
    }
  }

  async function exportPresets(): Promise<void> {
    isExporting.value = true
    try {
      const response = await fetch('/admin/tts/presets/custom')
      if (!response.ok) throw new Error('Failed to fetch presets')
      const presetsData = await response.json()

      const exportData: ExportData = {
        version: '1.0',
        exportedAt: new Date().toISOString(),
        type: 'presets',
        data: presetsData
      }

      downloadJson(exportData, `presets-export-${Date.now()}.json`)
      audit.log('export', 'presets', 'Exported TTS presets')
      toast.success('Presets exported successfully')
    } catch (e) {
      toast.error('Export failed', (e as Error).message)
    } finally {
      isExporting.value = false
    }
  }

  async function exportFullConfig(): Promise<void> {
    isExporting.value = true
    try {
      const [faqRes, presetsRes, llmRes] = await Promise.all([
        fetch('/admin/faq').catch(() => null),
        fetch('/admin/tts/presets/custom').catch(() => null),
        fetch('/admin/llm/params').catch(() => null)
      ])

      const exportData: ExportData = {
        version: '1.0',
        exportedAt: new Date().toISOString(),
        type: 'full',
        data: {
          faq: faqRes?.ok ? await faqRes.json() : null,
          presets: presetsRes?.ok ? await presetsRes.json() : null,
          llmParams: llmRes?.ok ? await llmRes.json() : null
        }
      }

      downloadJson(exportData, `full-config-export-${Date.now()}.json`)
      audit.log('export', 'config', 'Exported full configuration')
      toast.success('Configuration exported successfully')
    } catch (e) {
      toast.error('Export failed', (e as Error).message)
    } finally {
      isExporting.value = false
    }
  }

  async function importConfig(file: File): Promise<boolean> {
    isImporting.value = true
    try {
      const text = await file.text()
      const importData: ExportData = JSON.parse(text)

      if (!importData.version || !importData.type || !importData.data) {
        throw new Error('Invalid export file format')
      }

      switch (importData.type) {
        case 'faq':
          await importFaqData(importData.data)
          break
        case 'presets':
          await importPresetsData(importData.data)
          break
        case 'full':
          if (importData.data.faq) await importFaqData(importData.data.faq)
          if (importData.data.presets) await importPresetsData(importData.data.presets)
          break
        default:
          throw new Error(`Unknown export type: ${importData.type}`)
      }

      audit.log('import', importData.type, `Imported ${importData.type} configuration`)
      toast.success('Import successful', `Imported ${importData.type} configuration`)
      return true
    } catch (e) {
      toast.error('Import failed', (e as Error).message)
      return false
    } finally {
      isImporting.value = false
    }
  }

  async function importFaqData(faqData: Record<string, string>): Promise<void> {
    for (const [trigger, response] of Object.entries(faqData)) {
      await fetch('/admin/faq', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ trigger, response })
      })
    }
    await fetch('/admin/faq/save', { method: 'POST' })
  }

  async function importPresetsData(presetsData: Record<string, any>): Promise<void> {
    for (const [name, params] of Object.entries(presetsData)) {
      await fetch('/admin/tts/presets/custom', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, params })
      })
    }
  }

  function openFileDialog(): Promise<File | null> {
    return new Promise((resolve) => {
      const input = document.createElement('input')
      input.type = 'file'
      input.accept = '.json'
      input.onchange = (e) => {
        const file = (e.target as HTMLInputElement).files?.[0] || null
        resolve(file)
      }
      input.click()
    })
  }

  async function handleImport(): Promise<boolean> {
    const file = await openFileDialog()
    if (!file) return false
    return importConfig(file)
  }

  return {
    isExporting,
    isImporting,
    exportFaq,
    exportPresets,
    exportFullConfig,
    importConfig,
    handleImport
  }
}

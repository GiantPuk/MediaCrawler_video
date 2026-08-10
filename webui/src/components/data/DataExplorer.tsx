import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { FolderOpen, RefreshCw, Search, SlidersHorizontal } from 'lucide-react'
import { dataApi } from '@/lib/api'
import { FileCard } from './FileCard'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import type { DataFile } from '@/types/crawler'

type DataCategory = 'all' | 'search' | 'ranking' | 'content' | 'creators' | 'comments' | 'analysis' | 'media' | 'other'
type SortKey = 'modified_desc' | 'modified_asc' | 'name_asc' | 'name_desc' | 'size_desc' | 'records_desc'

const CATEGORY_ORDER: DataCategory[] = ['all', 'search', 'ranking', 'content', 'creators', 'comments', 'analysis', 'media', 'other']
const DATA_CATEGORIES = new Set<DataCategory>(CATEGORY_ORDER)

function normalizeCategory(value: string | null | undefined): Exclude<DataCategory, 'all'> | null {
  if (!value) return null
  return DATA_CATEGORIES.has(value as DataCategory) && value !== 'all' ? value as Exclude<DataCategory, 'all'> : null
}

function classifyFile(file: DataFile): Exclude<DataCategory, 'all'> {
  const apiCategory = normalizeCategory(file.category)
  if (apiCategory) return apiCategory
  const target = `${file.path}/${file.name}`.toLowerCase()
  if (/(comment|reply|sub_comment)/.test(target)) return 'comments'
  if (/(search_contents|direct_search|keyword|query)/.test(target)) return 'search'
  if (/(ranking_contents|hot_search|rank)/.test(target)) return 'ranking'
  if (/(creator_contents|author|user|profile|up_info|account)/.test(target)) return 'creators'
  if (/(transcript|subtitle|summary|result|analysis)/.test(target)) return 'analysis'
  if (/(detail_contents|content|note|post|article|tweet|weibo|bilibili|xhs|douyin|kuaishou|zhihu|tieba)/.test(target)) return 'content'
  if (/(media|video|image|download|cover|audio)/.test(target)) return 'media'
  return 'other'
}

function compareFiles(a: DataFile, b: DataFile, sortKey: SortKey) {
  if (sortKey === 'modified_desc') return b.modified_at - a.modified_at
  if (sortKey === 'modified_asc') return a.modified_at - b.modified_at
  if (sortKey === 'name_asc') return a.name.localeCompare(b.name)
  if (sortKey === 'name_desc') return b.name.localeCompare(a.name)
  if (sortKey === 'size_desc') return b.size - a.size
  return (b.record_count ?? -1) - (a.record_count ?? -1)
}

export function DataExplorer() {
  const { t } = useTranslation('data')
  const [activeCategory, setActiveCategory] = useState<DataCategory>('all')
  const [searchTerm, setSearchTerm] = useState('')
  const [typeFilter, setTypeFilter] = useState('all')
  const [sortKey, setSortKey] = useState<SortKey>('modified_desc')

  const { data, isLoading, refetch, isRefetching } = useQuery({
    queryKey: ['dataFiles'],
    queryFn: async () => {
      const { data } = await dataApi.getFiles()
      return data.files
    },
  })

  const files = data || []

  const enrichedFiles = useMemo(
    () => files.map((file) => ({ ...file, category: classifyFile(file) })),
    [files],
  )

  const categoryCounts = useMemo(() => {
    const counts: Record<DataCategory, number> = {
      all: files.length,
      search: 0,
      ranking: 0,
      content: 0,
      creators: 0,
      comments: 0,
      analysis: 0,
      media: 0,
      other: 0,
    }
    enrichedFiles.forEach((file) => {
      counts[file.category] += 1
    })
    return counts
  }, [enrichedFiles, files.length])

  const fileTypes = useMemo(
    () => Array.from(new Set(files.map((file) => file.type.toLowerCase()))).sort(),
    [files],
  )

  const displayFiles = useMemo(() => {
    const term = searchTerm.trim().toLowerCase()
    return enrichedFiles
      .filter((file) => activeCategory === 'all' || file.category === activeCategory)
      .filter((file) => typeFilter === 'all' || file.type.toLowerCase() === typeFilter)
      .filter((file) => {
        if (!term) return true
        return `${file.name} ${file.path}`.toLowerCase().includes(term)
      })
      .sort((a, b) => compareFiles(a, b, sortKey))
  }, [activeCategory, enrichedFiles, searchTerm, sortKey, typeFilter])

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="mb-4 flex flex-shrink-0 flex-col gap-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-mono font-bold text-cyber-neon-cyan glow-text-cyan tracking-wider">
              {t('explorer.title')}
            </h2>
            <Badge variant="default" className="font-mono">
              {t('explorer.records', { count: files.length })}
            </Badge>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            disabled={isRefetching}
            className="font-mono"
          >
            <RefreshCw className={`h-4 w-4 ${isRefetching ? 'animate-spin' : ''}`} />
            {t('explorer.rescan')}
          </Button>
        </div>

        {files.length > 0 ? (
          <div className="grid grid-cols-1 gap-2 md:grid-cols-[minmax(220px,1fr)_150px_190px]">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-cyber-text-muted" />
              <Input
                value={searchTerm}
                onChange={(event) => setSearchTerm(event.target.value)}
                placeholder={t('explorer.searchPlaceholder')}
                className="h-9 pl-9 text-xs"
              />
            </div>
            <Select value={typeFilter} onValueChange={setTypeFilter}>
              <SelectTrigger className="h-9 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">{t('explorer.allTypes')}</SelectItem>
                {fileTypes.map((type) => (
                  <SelectItem key={type} value={type}>.{type.toUpperCase()}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={sortKey} onValueChange={(value) => setSortKey(value as SortKey)}>
              <SelectTrigger className="h-9 text-xs">
                <SlidersHorizontal className="mr-2 h-4 w-4 text-cyber-text-muted" />
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="modified_desc">{t('explorer.sort.modifiedDesc')}</SelectItem>
                <SelectItem value="modified_asc">{t('explorer.sort.modifiedAsc')}</SelectItem>
                <SelectItem value="name_asc">{t('explorer.sort.nameAsc')}</SelectItem>
                <SelectItem value="name_desc">{t('explorer.sort.nameDesc')}</SelectItem>
                <SelectItem value="size_desc">{t('explorer.sort.sizeDesc')}</SelectItem>
                <SelectItem value="records_desc">{t('explorer.sort.recordsDesc')}</SelectItem>
              </SelectContent>
            </Select>
          </div>
        ) : null}
      </div>

      {isLoading ? (
        <div className="flex flex-1 items-center justify-center">
          <div className="text-cyber-text-muted font-mono animate-pulse">
            {t('explorer.loading')}
          </div>
        </div>
      ) : files.length === 0 ? (
        <div className="flex flex-1 flex-col items-center justify-center text-center">
          <div className="relative">
            <FolderOpen className="mb-4 h-16 w-16 text-cyber-neon-cyan/30" />
            <div className="absolute inset-0 bg-cyber-neon-cyan/10 blur-xl" />
          </div>
          <h3 className="mb-2 text-lg font-mono font-medium text-cyber-neon-cyan">
            {t('explorer.noData')}
          </h3>
          <p className="max-w-md text-sm text-cyber-text-muted font-mono">
            {t('explorer.noDataHint')}
          </p>
        </div>
      ) : (
        <div className="grid min-h-0 flex-1 grid-cols-1 gap-4 lg:grid-cols-[220px_minmax(0,1fr)]">
          <aside className="min-h-0 overflow-auto rounded-md border border-cyber-border-subtle bg-cyber-bg-secondary/50 p-2">
            <div className="mb-2 px-2 text-[11px] font-semibold uppercase tracking-wide text-cyber-text-muted">
              {t('explorer.categoryTitle')}
            </div>
            <div className="space-y-1">
              {CATEGORY_ORDER.filter((category) => category === 'all' || categoryCounts[category] > 0).map((category) => (
                <button
                  key={category}
                  onClick={() => setActiveCategory(category)}
                  className={`flex w-full items-center justify-between rounded-md px-3 py-2 text-left text-xs font-mono transition-all ${
                    activeCategory === category
                      ? 'border border-cyber-neon-cyan/60 bg-cyber-neon-cyan/15 text-cyber-text-primary'
                      : 'border border-transparent text-cyber-text-secondary hover:border-cyber-border-DEFAULT hover:bg-cyber-bg-tertiary hover:text-cyber-text-primary'
                  }`}
                >
                  <span>{t(`explorer.categories.${category}`)}</span>
                  <span className="text-cyber-text-muted">{categoryCounts[category]}</span>
                </button>
              ))}
            </div>
          </aside>

          <section className="flex min-h-0 flex-col overflow-hidden rounded-md border border-cyber-border-subtle bg-cyber-bg-secondary/30">
            <div className="flex flex-shrink-0 flex-wrap items-center justify-between gap-2 border-b border-cyber-border-subtle px-3 py-2 text-xs text-cyber-text-secondary">
              <span>{t('explorer.filteredRecords', { count: displayFiles.length, total: files.length })}</span>
              <span className="font-mono text-cyber-text-muted">{t(`explorer.categories.${activeCategory}`)}</span>
            </div>
            <div className="min-h-0 flex-1 overflow-auto p-3">
              {displayFiles.length === 0 ? (
                <div className="flex h-full min-h-48 items-center justify-center rounded-md border border-dashed border-cyber-border-subtle text-sm text-cyber-text-muted">
                  {t('explorer.noFilteredData')}
                </div>
              ) : (
                <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
                  {displayFiles.map((file) => (
                    <FileCard key={file.path} file={file} />
                  ))}
                </div>
              )}
            </div>
          </section>
        </div>
      )}
    </div>
  )
}

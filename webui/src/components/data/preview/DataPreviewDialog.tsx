import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { Download } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { dataApi } from '@/lib/api'
import { DataPreviewTable } from './DataPreviewTable'
import type { DataFile } from '@/types/crawler'

interface DataPreviewDialogProps {
  file: DataFile
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function DataPreviewDialog({ file, open, onOpenChange }: DataPreviewDialogProps) {
  const { t } = useTranslation('data')

  const { data, isLoading, error } = useQuery({
    queryKey: ['filePreview', file.path],
    queryFn: async () => {
      const { data } = await dataApi.getFileContent(file.path, 100)
      return data
    },
    enabled: open,
  })

  const handleDownload = () => {
    const url = dataApi.getDownloadUrl(file.path)
    window.open(url, '_blank')
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex h-[86vh] max-w-[min(1200px,96vw)] flex-col overflow-hidden">
        <DialogHeader className="flex-shrink-0">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <DialogTitle className="font-mono text-cyber-neon-cyan">
                {file.name}
              </DialogTitle>
              <Badge variant="outline" className="font-mono text-[10px]">
                .{file.type.toUpperCase()}
              </Badge>
              {data && (
                <Badge variant="default" className="font-mono text-[10px]">
                  {t('preview.records', { count: data.total })}
                </Badge>
              )}
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={handleDownload}
              className="font-mono text-xs"
            >
              <Download className="w-3 h-3 mr-1" />
              {t('preview.download')}
            </Button>
          </div>
        </DialogHeader>

        {/* 内容区域 */}
        <div className="flex-1 overflow-hidden min-h-0 mt-4">
          {isLoading ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-cyber-text-muted font-mono animate-pulse">
                {t('preview.loading')}
              </div>
            </div>
          ) : error ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-cyber-neon-pink font-mono">
                {t('preview.error')}
              </div>
            </div>
          ) : data && Array.isArray(data.data) ? (
            <DataPreviewTable
              data={data.data}
              columns={data.columns}
            />
          ) : data ? (
            <div className="h-full overflow-auto rounded-lg border border-cyber-border-DEFAULT bg-cyber-bg-tertiary/30">
              <pre className="p-4 text-xs leading-relaxed font-mono text-cyber-text-primary whitespace-pre-wrap break-words">
                {JSON.stringify(data.data, null, 2)}
              </pre>
            </div>
          ) : null}
        </div>
      </DialogContent>
    </Dialog>
  )
}

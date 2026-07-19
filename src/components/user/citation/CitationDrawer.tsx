import { Alert, Button, Drawer } from 'antd';
import { useUiStore } from '@/stores/uiStore';
import { useCitationDetail } from '@/hooks/chat/useCitationDetail';
import { LoadingState } from '@/components/user/common/LoadingState';
import { ErrorState } from '@/components/user/common/ErrorState';
import { SourceMetadata } from './SourceMetadata';

/** 引用详情抽屉：按 citation_id 拉取详情，处理无权限与加载失败 */
export function CitationDrawer() {
  const open = useUiStore((s) => s.citationDrawerOpen);
  const activeId = useUiStore((s) => s.activeCitationId);
  const close = useUiStore((s) => s.closeCitation);
  const { detail, loading, error, reload } = useCitationDetail(open ? activeId : null);

  return (
    <Drawer title="引用详情" open={open} onClose={close} width={420} destroyOnClose>
      {loading ? <LoadingState tip="加载引用" /> : null}
      {!loading && error ? (
        <ErrorState title="引用获取失败" description={error} onRetry={reload} />
      ) : null}
      {!loading && !error && detail ? (
        detail.access_denied ? (
          // 无权限：不展示真实地址与正文
          <Alert
            type="warning"
            showIcon
            message="无权查看该引用"
            description="您当前没有查看此文档来源的权限，请联系管理员申请授权。"
          />
        ) : (
          <>
            <SourceMetadata detail={detail} />
            {detail.can_open_source && detail.source_url ? (
              <Button
                type="primary"
                block
                style={{ marginTop: 16 }}
                href={detail.source_url}
                target="_blank"
                rel="noopener noreferrer"
              >
                打开原文
              </Button>
            ) : (
              <Alert
                style={{ marginTop: 16 }}
                type="info"
                showIcon
                message="当前无法打开原文"
                description="您没有打开该文档原文的权限，或文档已下线。"
              />
            )}
          </>
        )
      ) : null}
    </Drawer>
  );
}

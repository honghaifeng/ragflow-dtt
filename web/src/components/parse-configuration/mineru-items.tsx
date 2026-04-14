import { DocumentParserType } from '@/constants/knowledge';
import { useTranslate } from '@/hooks/common-hooks';
import { cn } from '@/lib/utils';
import {
  Form,
  InputNumber,
  Select,
  Slider,
  Switch,
  Flex,
  Input,
  Tooltip,
} from 'antd';
import { InfoCircleOutlined } from '@ant-design/icons';
import { DatasetConfigurationContainer } from '../dataset-configuration-container';

// MinerU配置不适用于这些解析方式
const excludedMethods = [
  DocumentParserType.Qa,
  DocumentParserType.Tag,
  DocumentParserType.Resume,
];

export const showMinerUItems = (
  parserId: DocumentParserType | undefined,
) => {
  return !excludedMethods.some((x) => x === parserId);
};

type MinerUItemsProps = {
  marginBottom?: boolean;
};

const MinerUItems = ({ marginBottom = false }: MinerUItemsProps) => {
  const { t } = useTranslate('knowledgeConfiguration');

  return (
    <DatasetConfigurationContainer className={cn({ 'mb-4': marginBottom })}>
      <Form.Item
        name={['parser_config', 'mineru', 'enable_ocr']}
        label={
          <span>
            OCR增强{' '}
            <Tooltip title="开启后将对扫描件/图片类PDF使用OCR识别文字，提升解析质量但会增加处理时间">
              <InfoCircleOutlined />
            </Tooltip>
          </span>
        }
        initialValue={true}
        valuePropName="checked"
      >
        <Switch />
      </Form.Item>

      <Form.Item
        name={['parser_config', 'mineru', 'parse_mode']}
        label="解析模式"
        initialValue="auto"
        tooltip="auto: 自动检测PDF类型选择最优解析模式; ocr: 强制OCR模式; txt: 强制文本模式"
      >
        <Select
          options={[
            { label: '自动检测 (Auto)', value: 'auto' },
            { label: '强制OCR模式', value: 'ocr' },
            { label: '强制文本模式', value: 'txt' },
          ]}
        />
      </Form.Item>

      <Form.Item
        label="分块大小 (Token数)"
        tooltip="每个文本块的最大token数量，较大的块保留更多上下文但检索精度可能降低"
      >
        <Flex gap={20} align="center">
          <Flex flex={1}>
            <Form.Item
              name={['parser_config', 'mineru', 'chunk_token_num']}
              noStyle
              initialValue={512}
            >
              <Slider min={64} max={4096} step={64} style={{ width: '100%' }} />
            </Form.Item>
          </Flex>
          <Form.Item
            name={['parser_config', 'mineru', 'chunk_token_num']}
            noStyle
          >
            <InputNumber min={64} max={4096} step={64} />
          </Form.Item>
        </Flex>
      </Form.Item>

      <Form.Item
        label="分块重叠 (Token数)"
        tooltip="相邻文本块之间的重叠token数量，较大的重叠可以避免上下文丢失"
      >
        <Flex gap={20} align="center">
          <Flex flex={1}>
            <Form.Item
              name={['parser_config', 'mineru', 'chunk_overlap']}
              noStyle
              initialValue={128}
            >
              <Slider min={0} max={512} step={16} style={{ width: '100%' }} />
            </Form.Item>
          </Flex>
          <Form.Item
            name={['parser_config', 'mineru', 'chunk_overlap']}
            noStyle
          >
            <InputNumber min={0} max={512} step={16} />
          </Form.Item>
        </Flex>
      </Form.Item>

      <Form.Item
        name={['parser_config', 'mineru', 'table_strategy']}
        label="表格处理策略"
        initialValue="html"
        tooltip="表格内容的处理方式：HTML保留表格结构最完整，Markdown适合阅读，文本模式最简单"
      >
        <Select
          options={[
            { label: 'HTML (保留结构)', value: 'html' },
            { label: 'Markdown (易读)', value: 'markdown' },
            { label: '纯文本 (简单)', value: 'text' },
          ]}
        />
      </Form.Item>

      <Form.Item
        name={['parser_config', 'mineru', 'image_handling']}
        label="图片处理"
        initialValue="ocr"
        tooltip="文档中图片的处理方式：OCR识别图中文字，描述用AI生成图片描述，忽略则跳过图片"
      >
        <Select
          options={[
            { label: 'OCR识别文字', value: 'ocr' },
            { label: 'AI生成描述', value: 'description' },
            { label: '忽略图片', value: 'ignore' },
          ]}
        />
      </Form.Item>

      <Form.Item
        name={['parser_config', 'mineru', 'layout_analysis']}
        label="版面分析"
        initialValue={true}
        valuePropName="checked"
        tooltip="使用深度学习模型分析文档版面布局（标题、段落、表格、图片区域），提升解析准确度"
      >
        <Switch />
      </Form.Item>

      <Form.Item
        name={['parser_config', 'mineru', 'formula_recognition']}
        label="公式识别"
        initialValue={false}
        valuePropName="checked"
        tooltip="是否识别文档中的数学公式并转换为LaTeX格式"
      >
        <Switch />
      </Form.Item>

      <Form.Item
        name={['parser_config', 'mineru', 'header_footer_removal']}
        label="去除页眉页脚"
        initialValue={true}
        valuePropName="checked"
        tooltip="自动去除PDF中的页眉、页脚和页码"
      >
        <Switch />
      </Form.Item>

      <Form.Item
        name={['parser_config', 'mineru', 'custom_separators']}
        label="自定义分割符"
        tooltip="自定义文本块分割符号，每行一个正则表达式。留空则使用默认分割规则"
      >
        <Input.TextArea
          rows={3}
          placeholder={`例如：\n\\n{2,}  (两个以上空行)\n^第[一二三四五六七八九十]+章  (章节标题)\n^\\d+\\.\\s  (数字编号)`}
        />
      </Form.Item>
    </DatasetConfigurationContainer>
  );
};

export default MinerUItems;

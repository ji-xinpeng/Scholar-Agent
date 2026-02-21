import os
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict


def pdf_to_markdown(pdf_path, output_dir=None):
    """
    使用 Marker 将 PDF 文件转换为 Markdown
    
    Args:
        pdf_path: PDF 文件路径
        output_dir: 输出目录，默认为 PDF 文件所在目录
    """
    if not os.path.exists(pdf_path):
        print(f"错误: 文件 {pdf_path} 不存在")
        return
    
    if output_dir is None:
        output_dir = os.path.dirname(pdf_path)
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    print(f"正在加载模型...")
    artifact_dict = create_model_dict()
    
    print(f"正在转换 PDF: {pdf_path}")
    converter = PdfConverter(artifact_dict, renderer="marker.renderers.markdown.MarkdownRenderer")
    rendered = converter(pdf_path)
    
    pdf_filename = os.path.basename(pdf_path)
    md_filename = os.path.splitext(pdf_filename)[0] + ".md"
    md_path = os.path.join(output_dir, md_filename)
    
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(rendered.markdown)
    
    print(f"转换完成！Markdown 文件已保存到: {md_path}")
    print(f"转换了 {converter.page_count} 页")
    
    return md_path


if __name__ == "__main__":
    import sys
    
    pdf_path = "/Users/jixinpeng/Desktop/Agent/input.pdf"
    output_dir = "/Users/jixinpeng/Desktop/Agent/out"
    pdf_to_markdown(pdf_path, output_dir)


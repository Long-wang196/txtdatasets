import re
import json

# 更新后的 locations 列表，处理带编号的 “研究生公寓” 项
locations = ['体育馆', '图书馆', '校医院', '思雨楼', '教学楼', '实验室', '南门', '北门',
             '东门', '西门', '操场', '停车场', '行政楼', '食堂', '宿舍楼', '凌云楼', '齐云楼',
             '第二留学生公寓', '胡杨楼', '田径场', '留学生公寓', '毓秀湖', '校友广场1', '思雨楼',
             '逸夫科学馆', '正门', '萃英大酒店和贵勤楼', '天演楼', '学生活动中心', '分析测试中心',
             '格致楼', '第一化学楼', '逸夫生物楼', '南二门', '网球场', '飞云楼', '计算机中心', '祁连堂',
             '后勤保障部', '篮球场', '观云楼', '南一门', '排球场', '专家楼', '校友广场2', '兰州大学出版社',
             '新体育馆', '校医院', '岫云楼', '体育馆', '研究生公寓\\d+#', '第二化学楼', '校史馆', '积石堂', "宿舍楼", "家属院", "澡堂"]

directions = ["东南", "西南", "东北", "西北", "正东", "正西", "正南", "正北", "东", "西", "南", "北"]
position_words = ["位于", "在", "临近", "靠近"]

locations = sorted(locations, key=lambda x: -len(x))
# 结合实体、介词和方向的正则表达式
entity_pattern = r'|'.join(locations)
direction_pattern = r'|'.join(directions)
position_pattern = r'|'.join(position_words)

# 定义两个匹配结构的正则表达式
pattern1 = re.compile(rf"({entity_pattern})({position_pattern})({entity_pattern})的({direction_pattern})")
pattern2 = re.compile(rf"({position_pattern})({entity_pattern})的({direction_pattern})")


# 函数：提取实体和标注类型
def extract_entities(sentence, current_subject=None):
    entities = []
    is_subject_present = False  # 检查是否存在主语

    # 将句子按标点符号切分为子句
    clauses = re.split(r'[，。]', sentence)

    for clause in clauses:
        if not clause.strip():
            continue

        # print(f"Processing clause: {clause}")  # 调试信息

        # 先尝试匹配主语，宾语等
        matches1 = list(pattern1.finditer(clause))
        if matches1:
            for match in matches1:
                subj, prep, obj, rel = match.groups()
                # print(f"Match found with subject: {subj}")  # 调试输出
                entities.append((subj, 'SUBJ'))
                is_subject_present = True  # 找到了主语
                entities.append((prep, 'PREP'))
                entities.append((obj, 'OBJ'))
                entities.append((rel, 'REL'))
                current_subject = subj  # 更新当前主语
            continue

        # 检查是否匹配到宾语和介词，没有匹配到主语
        matches2 = list(pattern2.finditer(clause))
        if matches2:
            for match in matches2:
                prep, obj, rel = match.groups()
                if current_subject:
                    # print(f"Reusing subject: {current_subject} for clause: {clause}")  # 调试输出
                    entities.append((current_subject, 'SUBJ'))  # 使用最近的主语
                    is_subject_present = True
                entities.append((prep, 'PREP'))
                entities.append((obj, 'OBJ'))
                entities.append((rel, 'REL'))
            continue

    # 如果当前子句没有找到主语并且之前也没有主语，使用默认主语
    if not is_subject_present and not current_subject:
        default_subject = "UNKNOWN_SUBJ"
        entities.insert(0, (default_subject, 'SUBJ'))  # 为句子补充默认主语
        # print(f"No subject found, using default subject: {default_subject}")  # 调试输出

    return entities


# 函数：生成BIO标注
def generate_bio(sentence, entities):
    bio_labels = ['O'] * len(sentence)

    for entity, label_type in entities:
        start_idx = sentence.find(entity)
        while start_idx != -1:  # 查找所有出现的实体
            if label_type == 'PREP':
                bio_labels[start_idx] = 'O'
                for i in range(1, len(entity)):
                    bio_labels[start_idx + i] = 'O'
            else:
                bio_labels[start_idx] = 'B-' + label_type
                for i in range(1, len(entity)):
                    bio_labels[start_idx + i] = 'I-' + label_type
            start_idx = sentence.find(entity, start_idx + len(entity))

    return bio_labels


# 函数：处理句子标注
def process_sentence(sentence):
    sub_sentences = re.split(r'([，。])', sentence.strip())  # 同时保留标点符号
    all_tokens = []  # 用于存储所有子句的tokens
    all_labels = []  # 用于存储所有子句的labels
    current_subject = None  # 用于追踪主语的变化

    for sub_sentence in sub_sentences:
        if sub_sentence.strip():  # 忽略空子句
            if sub_sentence in '，。':  # 如果是标点符号，直接加到 tokens 和 labels 中
                all_tokens.append(sub_sentence)
                all_labels.append('O')  # 标点符号标注为 'O'
                continue

            # 提取实体和关系
            entities = extract_entities(sub_sentence)

            # 追踪主语
            if entities and entities[0][1] == 'SUBJ':
                current_subject = entities[0][0]  # 更新主语
            else:
                if current_subject:
                    # 如果当前子句没有主语，但之前有主语，复用该主语
                    entities.insert(0, (current_subject, 'SUBJ'))

            # 生成BIO标注
            labels = generate_bio(sub_sentence, entities)
            all_tokens.extend(list(sub_sentence))  # 合并所有子句的token
            all_labels.extend(labels)  # 合并所有子句的label

    return [(all_tokens, all_labels)]  # 返回整个句子合并后的标注



# 将标注结果写入JSON文件
def write_to_json(labeled_sentences, filename):
    data = []
    for tokens, labels in labeled_sentences:
        entry = {"tokens": tokens, "labels": labels}
        data.append(entry)

    with open(filename, 'w', encoding='utf-8') as jsonf:
        json.dump(data, jsonf, ensure_ascii=False, indent=4)

# 检查并修正标签的函数
def correct_labels(data):
    # 要检查的目标名称列表（复合地点名称）
    targets = ["南二门", "南一门", "南门", "东门", "西门", "正门", "北门"]

    for entry in data:
        tokens = entry[0]
        labels = entry[1]

        # 遍历 tokens 列表，寻找目标词汇
        for target in targets:
            target_len = len(target)
            for i in range(len(tokens) - target_len + 1):
                # 检查当前窗口是否与目标匹配
                if tokens[i:i + target_len] == list(target):
                    # 检查最后两个字符的标签是否为 'I-SUBJ'
                    if all(labels[i+j] == 'I-SUBJ' for j in range(1, target_len)):
                        # 检查第一个字符的标签是否为 'B-SUBJ'
                        if labels[i] != 'B-SUBJ':
                            # print(f"在索引 {i} 发现问题：'{tokens[i]}' 的标签为 {labels[i]}，需要修正为 'B-SUBJ'")
                            # 修正标签
                            labels[i] = 'B-SUBJ'

    return data

if __name__ == "__main__":
    input_filename = "../datatxt/SO_test_extended_direction_data_large.txt"
    output_filename = "../datajson/SO_test_gened_bio_data.json"

    # 从txt文件中读取句子
    with open(input_filename, 'r', encoding='utf-8') as file:
        sentences = file.readlines()

    all_labeled_sentences = []

    for sentence in sentences:
        # 处理每个句子并生成标注
        labeled_sentences = process_sentence(sentence.strip())
        all_labeled_sentences.extend(labeled_sentences)

        # 打印调试信息
    # print(labeled_sentences)
    # for i, j in zip(labeled_sentences[0][0], labeled_sentences[0][1]):
    #     print(i, j, sep='\t')  # 使用制表符分隔，每对 tokens 和 labels 在同一行输出

    output_data = correct_labels(all_labeled_sentences)

    # 将所有标注结果写入JSON文件
    # write_to_json(output_data, output_filename)
    #
    # print("标注结果已保存到", output_filename)


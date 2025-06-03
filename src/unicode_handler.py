import unicodedata
import re
import logging
from typing import Tuple, Optional

# ログ設定
logger = logging.getLogger(__name__)

# サロゲートペア範囲の定義
SURROGATE_PAIR_PATTERN = re.compile(r'[\ud800-\udfff]')

# 数学記号マッピング辞書（サロゲートペアから標準Unicode文字への変換）
MATH_SYMBOL_MAPPING = {
    # Mathematical Bold Letters (U+1D400-U+1D433)
    '\U0001d400': 'A',  # 𝐀 → A
    '\U0001d401': 'B',  # 𝐁 → B
    '\U0001d402': 'C',  # 𝐂 → C
    '\U0001d403': 'D',  # 𝐃 → D
    '\U0001d404': 'E',  # 𝐄 → E
    '\U0001d405': 'F',  # 𝐅 → F
    '\U0001d406': 'G',  # 𝐆 → G
    '\U0001d407': 'H',  # 𝐇 → H
    '\U0001d408': 'I',  # 𝐈 → I
    '\U0001d409': 'J',  # 𝐉 → J
    '\U0001d40a': 'K',  # 𝐊 → K
    '\U0001d40b': 'L',  # 𝐋 → L
    '\U0001d40c': 'M',  # 𝐌 → M
    '\U0001d40d': 'N',  # 𝐍 → N
    '\U0001d40e': 'O',  # 𝐎 → O
    '\U0001d40f': 'P',  # 𝐏 → P
    '\U0001d410': 'Q',  # 𝐐 → Q
    '\U0001d411': 'R',  # 𝐑 → R
    '\U0001d412': 'S',  # 𝐒 → S
    '\U0001d413': 'T',  # 𝐓 → T
    '\U0001d414': 'U',  # 𝐔 → U
    '\U0001d415': 'V',  # 𝐕 → V
    '\U0001d416': 'W',  # 𝐖 → W
    '\U0001d417': 'X',  # 𝐗 → X
    '\U0001d418': 'Y',  # 𝐘 → Y
    '\U0001d419': 'Z',  # 𝐙 → Z
    '\U0001d41a': 'a',  # 𝐚 → a
    '\U0001d41b': 'b',  # 𝐛 → b
    '\U0001d41c': 'c',  # 𝐜 → c
    '\U0001d41d': 'd',  # 𝐝 → d
    '\U0001d41e': 'e',  # 𝐞 → e
    '\U0001d41f': 'f',  # 𝐟 → f
    '\U0001d420': 'g',  # 𝐠 → g
    '\U0001d421': 'h',  # 𝐡 → h
    '\U0001d422': 'i',  # 𝐢 → i
    '\U0001d423': 'j',  # 𝐣 → j
    '\U0001d424': 'k',  # 𝐤 → k
    '\U0001d425': 'l',  # 𝐥 → l
    '\U0001d426': 'm',  # 𝐦 → m
    '\U0001d427': 'n',  # 𝐧 → n
    '\U0001d428': 'o',  # 𝐨 → o
    '\U0001d429': 'p',  # 𝐩 → p
    '\U0001d42a': 'q',  # 𝐪 → q
    '\U0001d42b': 'r',  # 𝐫 → r
    '\U0001d42c': 's',  # 𝐬 → s
    '\U0001d42d': 't',  # 𝐭 → t
    '\U0001d42e': 'u',  # 𝐮 → u
    '\U0001d42f': 'v',  # 𝐯 → v
    '\U0001d430': 'w',  # 𝐰 → w
    '\U0001d431': 'x',  # 𝐱 → x
    '\U0001d432': 'y',  # 𝐲 → y
    '\U0001d433': 'z',  # 𝐳 → z
    
    # Mathematical Italic Letters (U+1D434-U+1D467)
    '\U0001d434': 'A',  # 𝐴 → A (italic)
    '\U0001d435': 'B',  # 𝐵 → B (italic)
    '\U0001d436': 'C',  # 𝐶 → C (italic)
    '\U0001d437': 'D',  # 𝐷 → D (italic)
    '\U0001d438': 'E',  # 𝐸 → E (italic)
    '\U0001d439': 'F',  # 𝐹 → F (italic)
    '\U0001d43a': 'G',  # 𝐺 → G (italic)
    '\U0001d43b': 'H',  # 𝐻 → H (italic)
    '\U0001d43c': 'I',  # 𝐼 → I (italic)
    '\U0001d43d': 'J',  # 𝐽 → J (italic)
    '\U0001d43e': 'K',  # 𝐾 → K (italic)
    '\U0001d43f': 'L',  # 𝐿 → L (italic)
    '\U0001d440': 'M',  # 𝑀 → M (italic)
    '\U0001d441': 'N',  # 𝑁 → N (italic)
    '\U0001d442': 'O',  # 𝑂 → O (italic)
    '\U0001d443': 'P',  # 𝑃 → P (italic)
    '\U0001d444': 'Q',  # 𝑄 → Q (italic)
    '\U0001d445': 'R',  # 𝑅 → R (italic)
    '\U0001d446': 'S',  # 𝑆 → S (italic)
    '\U0001d447': 'T',  # 𝑇 → T (italic)
    '\U0001d448': 'U',  # 𝑈 → U (italic)
    '\U0001d449': 'V',  # 𝑉 → V (italic)
    '\U0001d44a': 'W',  # 𝑊 → W (italic)
    '\U0001d44b': 'X',  # 𝑋 → X (italic)
    '\U0001d44c': 'Y',  # 𝑌 → Y (italic)
    '\U0001d44d': 'Z',  # 𝑍 → Z (italic)
    '\U0001d44e': 'a',  # 𝑎 → a (italic)
    '\U0001d44f': 'b',  # 𝑏 → b (italic)
    '\U0001d450': 'c',  # 𝑐 → c (italic)
    '\U0001d451': 'd',  # 𝑑 → d (italic)
    '\U0001d452': 'e',  # 𝑒 → e (italic)
    '\U0001d453': 'f',  # 𝑓 → f (italic)
    '\U0001d454': 'g',  # 𝑔 → g (italic)
    '\U0001d456': 'i',  # 𝑖 → i (italic) (U+1D455 is reserved)
    '\U0001d457': 'j',  # 𝑗 → j (italic)
    '\U0001d458': 'k',  # 𝑘 → k (italic)
    '\U0001d459': 'l',  # 𝑙 → l (italic)
    '\U0001d45a': 'm',  # 𝑚 → m (italic)
    '\U0001d45b': 'n',  # 𝑛 → n (italic)
    '\U0001d45c': 'o',  # 𝑜 → o (italic)
    '\U0001d45d': 'p',  # 𝑝 → p (italic)
    '\U0001d45e': 'q',  # 𝑞 → q (italic)
    '\U0001d45f': 'r',  # 𝑟 → r (italic)
    '\U0001d460': 's',  # 𝑠 → s (italic)
    '\U0001d461': 't',  # 𝑡 → t (italic)
    '\U0001d462': 'u',  # 𝑢 → u (italic)
    '\U0001d463': 'v',  # 𝑣 → v (italic)
    '\U0001d464': 'w',  # 𝑤 → w (italic)
    '\U0001d465': 'x',  # 𝑥 → x (italic)
    '\U0001d466': 'y',  # 𝑦 → y (italic)
    '\U0001d467': 'z',  # 𝑧 → z (italic)
}

def detect_surrogate_pairs(text: str) -> bool:
    """
    テキスト内にサロゲートペア文字が含まれているかチェックする
    
    Args:
        text: チェックするテキスト
        
    Returns:
        サロゲートペアが含まれている場合True
    """
    return bool(SURROGATE_PAIR_PATTERN.search(text))

def get_surrogate_positions(text: str) -> list:
    """
    テキスト内のサロゲートペア文字の位置を取得する
    
    Args:
        text: チェックするテキスト
        
    Returns:
        サロゲートペアの位置リスト [(start, end, char), ...]
    """
    positions = []
    for match in SURROGATE_PAIR_PATTERN.finditer(text):
        positions.append((match.start(), match.end(), match.group()))
    return positions

def normalize_unicode_text(text: str, aggressive: bool = False) -> Tuple[str, bool]:
    """
    Unicodeテキストを正規化し、サロゲートペア文字を処理する
    
    Args:
        text: 処理するテキスト
        aggressive: より積極的な変換を行うかどうか
        
    Returns:
        tuple: (正規化されたテキスト, 変更が行われたかどうか)
    """
    original_text = text
    modified = False
    
    try:
        # まずUTF-8エンコードを試す
        text.encode('utf-8', errors='strict')
        # エンコードに成功した場合、軽微な正規化のみ実行
        normalized = unicodedata.normalize('NFC', text)
        return normalized, normalized != original_text
    except UnicodeEncodeError:
        logger.info("サロゲートペア文字が検出されました。正規化処理を開始します。")
        modified = True
    
    # NFD正規化を実行
    try:
        text = unicodedata.normalize('NFD', text)
    except Exception as e:
        logger.warning(f"NFD正規化でエラーが発生しました: {e}")
    
    # 数学記号マッピングを適用
    for unicode_char, replacement in MATH_SYMBOL_MAPPING.items():
        if unicode_char in text:
            text = text.replace(unicode_char, replacement)
            logger.info(f"数学記号を変換しました: {unicode_char} → {replacement}")
    
    # サロゲートペア文字の処理
    if detect_surrogate_pairs(text):
        positions = get_surrogate_positions(text)
        logger.warning(f"残存するサロゲートペア文字: {len(positions)}個")
        
        for pos_start, pos_end, char in reversed(positions):  # 後ろから処理
            char_code = ord(char)
            logger.warning(f"位置 {pos_start}: サロゲートペア文字 U+{char_code:04X}")
            
            if aggressive:
                # 積極的モード: 文字を削除
                text = text[:pos_start] + text[pos_end:]
                logger.info(f"サロゲートペア文字を削除しました: U+{char_code:04X}")
            else:
                # 保守的モード: 安全な文字に置換
                replacement = '?'  # または '[MATH]' など
                text = text[:pos_start] + replacement + text[pos_end:]
                logger.info(f"サロゲートペア文字を置換しました: U+{char_code:04X} → {replacement}")
    
    # NFC正規化を実行
    try:
        text = unicodedata.normalize('NFC', text)
    except Exception as e:
        logger.warning(f"NFC正規化でエラーが発生しました: {e}")
    
    # 最終的なUTF-8検証
    try:
        text.encode('utf-8', errors='strict')
        logger.info("UTF-8エンコーディング検証: 成功")
    except UnicodeEncodeError as e:
        logger.error(f"UTF-8エンコーディング検証: 失敗 - {e}")
        # 最後の手段: errorsパラメータで安全に処理
        text = text.encode('utf-8', errors='replace').decode('utf-8')
        logger.warning("強制的にUTF-8安全な文字列に変換しました")
    
    return text, modified

def safe_encode_text(text: str, encoding: str = 'utf-8') -> bytes:
    """
    テキストを安全にエンコードする
    
    Args:
        text: エンコードするテキスト
        encoding: 使用するエンコーディング
        
    Returns:
        エンコードされたバイト列
    """
    try:
        return text.encode(encoding, errors='strict')
    except UnicodeEncodeError:
        logger.warning("安全なエンコーディングモードに切り替えます")
        # まず正規化を試す
        normalized_text, _ = normalize_unicode_text(text)
        try:
            return normalized_text.encode(encoding, errors='strict')
        except UnicodeEncodeError:
            # それでも失敗した場合は置換モードを使用
            return text.encode(encoding, errors='replace')

def validate_text_for_api(text: str) -> Tuple[bool, Optional[str]]:
    """
    テキストがAPI呼び出しに安全かどうかを検証する
    
    Args:
        text: 検証するテキスト
        
    Returns:
        tuple: (安全かどうか, エラーメッセージ)
    """
    try:
        # UTF-8エンコードテスト
        text.encode('utf-8', errors='strict')
        
        # サロゲートペアチェック
        if detect_surrogate_pairs(text):
            return False, "サロゲートペア文字が含まれています"
        
        return True, None
    except UnicodeEncodeError as e:
        return False, f"UnicodeEncodeError: {str(e)}"

if __name__ == "__main__":
    # テスト用コード
    test_text = "これはテスト用の文字列です。数学記号: 𝐀𝐁𝐂"
    print(f"元のテキスト: {test_text}")
    
    normalized, modified = normalize_unicode_text(test_text)
    print(f"正規化後: {normalized}")
    print(f"変更されたか: {modified}")
    
    is_safe, error_msg = validate_text_for_api(normalized)
    print(f"API安全性: {is_safe}")
    if error_msg:
        print(f"エラー: {error_msg}")
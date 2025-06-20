"""
Grafik oluşturma fonksiyonları modülü.
Bu modül, veri görselleştirme için çeşitli grafik oluşturma fonksiyonlarını içerir.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO
import base64

def plot_to_base64(fig):
    """
    Matplotlib figürünü base64 formatına dönüştürür
    """
    buf = BytesIO()
    fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    img_str = base64.b64encode(buf.read()).decode('utf-8')
    buf.close()
    return img_str

def create_bar_chart(df, column, title=None, limit=10):
    """
    Bir sütun için çubuk grafik oluşturur
    """
    if column not in df.columns:
        return None
    
    # Değer sayılarını hesapla
    value_counts = df[column].value_counts().nlargest(limit)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    value_counts.plot(kind='bar', ax=ax)
    
    if title:
        ax.set_title(title)
    else:
        ax.set_title(f'{column} Dağılımı')
    
    ax.set_xlabel(column)
    ax.set_ylabel('Sayı')
    
    plt.tight_layout()
    
    return fig

def create_pie_chart(df, column, title=None, limit=5):
    """
    Bir sütun için pasta grafik oluşturur
    """
    if column not in df.columns:
        return None
    
    # Değer sayılarını hesapla
    value_counts = df[column].value_counts().nlargest(limit)
    
    # Kalan değerleri "Diğer" olarak grupla
    total = df[column].count()
    if total > value_counts.sum():
        value_counts["Diğer"] = total - value_counts.sum()
    
    fig, ax = plt.subplots(figsize=(10, 6))
    value_counts.plot(kind='pie', ax=ax, autopct='%1.1f%%')
    
    if title:
        ax.set_title(title)
    else:
        ax.set_title(f'{column} Dağılımı')
    
    ax.set_ylabel('')
    
    plt.tight_layout()
    
    return fig

def create_scatter_plot(df, x_column, y_column, title=None):
    """
    İki sayısal sütun için saçılım grafiği oluşturur
    """
    if x_column not in df.columns or y_column not in df.columns:
        return None
    
    # Sütunların sayısal olduğundan emin ol
    try:
        x_data = pd.to_numeric(df[x_column], errors='coerce')
        y_data = pd.to_numeric(df[y_column], errors='coerce')
    except:
        return None
    
    # NaN değerleri filtrele
    mask = ~(x_data.isnull() | y_data.isnull())
    x_data = x_data[mask]
    y_data = y_data[mask]
    
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.scatter(x_data, y_data, alpha=0.5)
    
    if title:
        ax.set_title(title)
    else:
        ax.set_title(f'{x_column} vs {y_column}')
    
    ax.set_xlabel(x_column)
    ax.set_ylabel(y_column)
    
    # En uygun doğru ekle
    if len(x_data) >= 2:  # Regresyon için en az 2 nokta gerekir
        try:
            z = np.polyfit(x_data, y_data, 1)
            p = np.poly1d(z)
            ax.plot(x_data, p(x_data), "r--", alpha=0.8)
        except:
            pass
    
    plt.tight_layout()
    
    return fig 
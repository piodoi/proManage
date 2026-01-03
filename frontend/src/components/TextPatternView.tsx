import { useState, useRef } from 'react';
import { useAuth } from '../App';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useI18n } from '../lib/i18n';
import { Save, Upload } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';

type FieldPattern = {
  field_name: string;
  label_text: string;
  line_offset: number;
};

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function TextPatternView() {
  const { token, user } = useAuth();
  const { t } = useI18n();
  const [pdfText, setPdfText] = useState<string>('');
  const [selectedLabel, setSelectedLabel] = useState<string>('');
  const [selectedLabelStart, setSelectedLabelStart] = useState<number | null>(null);
  const [currentField, setCurrentField] = useState<string>('amount');
  const [fieldPatterns, setFieldPatterns] = useState<Map<string, FieldPattern>>(new Map());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [patternName, setPatternName] = useState('');
  const [supplier, setSupplier] = useState('');
  const [billType, setBillType] = useState<'rent' | 'utilities' | 'ebloc' | 'other'>('utilities');
  const [lineOffsets, setLineOffsets] = useState<Map<string, number>>(new Map());
  const textAreaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [highlightedLine, setHighlightedLine] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<string>('create');
  
  // Pattern matching state
  const [matchingPdf, setMatchingPdf] = useState<File | null>(null);
  const [matches, setMatches] = useState<any[]>([]);
  const [extractionResult, setExtractionResult] = useState<any | null>(null);
  const [matchingPatterns, setMatchingPatterns] = useState(false);
  
  // Edit Pattern state (admin only)
  const [selectedPatternId, setSelectedPatternId] = useState<string>('');
  const [editingPattern, setEditingPattern] = useState<any | null>(null);
  const [editMatches, setEditMatches] = useState<any[]>([]);
  const [editPdfFile, setEditPdfFile] = useState<File | null>(null);
  
  const fieldOptions = [
    { value: 'amount', label: t('common.amount') },
    { value: 'currency', label: t('common.currency') || 'Currency' },
    { value: 'due_date', label: t('bill.dueDate') },
    { value: 'bill_date', label: t('bill.billDate') || 'Bill Date' },
    { value: 'iban', label: 'IBAN' },
    { value: 'bill_number', label: t('bill.billNumber') },
    { value: 'contract_id', label: t('supplier.contractId') },
    { value: 'payment_details', label: t('common.paymentDetails') },
    { value: 'address', label: t('property.address') },
    { value: 'legal_name', label: t('bill.legalName') || 'Legal Name' },
  ];

  const scrollToLine = (lineNum: number) => {
    if (textAreaRef.current && lineNum >= 0) {
      const lines = pdfText.split('\n');
      if (lineNum < lines.length) {
        // Calculate character position for the line
        let charPos = 0;
        for (let i = 0; i < lineNum; i++) {
          charPos += lines[i].length + 1; // +1 for newline
        }
        const lineEnd = charPos + lines[lineNum].length;
        
        // Select the line
        textAreaRef.current.focus();
        textAreaRef.current.setSelectionRange(charPos, lineEnd);
        
        // Check if line is already in view before scrolling
        const lineHeight = 20; // Approximate line height
        const targetScrollTop = lineNum * lineHeight;
        const currentScrollTop = textAreaRef.current.scrollTop;
        const visibleHeight = textAreaRef.current.clientHeight;
        const visibleStart = currentScrollTop;
        const visibleEnd = currentScrollTop + visibleHeight;
        
        // Only scroll if line is not already visible
        if (targetScrollTop < visibleStart || targetScrollTop > visibleEnd - lineHeight) {
          textAreaRef.current.scrollTop = targetScrollTop;
          textAreaRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
      }
    }
  };

  const handleFileUpload = async (file: File) => {
    if (!token) return;
    setLoading(true);
    setError('');
    try {
      const formData = new FormData();
      formData.append('file', file);
      const response = await fetch(`${API_URL}/text-patterns/upload-pdf`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: formData,
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to upload PDF');
      }
      
      const data = await response.json();
      setPdfText(data.text);
      setSuccess('PDF uploaded successfully');
      setTimeout(() => setSuccess(''), 3000);
    } catch (err: any) {
      setError(err.message || 'Error uploading PDF');
    } finally {
      setLoading(false);
    }
  };

  const handleTextSelection = () => {
    const textarea = textAreaRef.current;
    if (!textarea) return;
    
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const selectedText = pdfText.substring(start, end).trim();
    
    if (!selectedText) return;
    
    // Save label and use current line offset
    const currentOffset = lineOffsets.get(currentField) || 0;
    
    // Save label position for highlighting
    setSelectedLabelStart(start);
    
    // Save pattern (only label_text and line_offset, no value_text)
    const pattern: FieldPattern = {
      field_name: currentField,
      label_text: selectedText,
      line_offset: currentOffset,
    };
    
    setFieldPatterns(prev => {
      const newMap = new Map(prev);
      newMap.set(currentField, pattern);
      return newMap;
    });
    
    setSelectedLabel(selectedText);
    setSuccess(`Label saved for ${fieldOptions.find(f => f.value === currentField)?.label} (offset: ${currentOffset})`);
    setTimeout(() => setSuccess(''), 3000);
    
    // Highlight target line if offset > 0
    if (currentOffset > 0 && start !== null) {
      highlightTargetLine(start, currentOffset);
    }
  };
  
  const highlightTargetLine = (labelStart: number, offset: number) => {
    const lines = pdfText.split('\n');
    const labelLineNum = pdfText.substring(0, labelStart).split('\n').length - 1;
    const targetLineNum = labelLineNum + offset;
    
    if (targetLineNum >= 0 && targetLineNum < lines.length) {
      setHighlightedLine(targetLineNum);
      scrollToLine(targetLineNum);
    } else {
      setHighlightedLine(null);
    }
  };
  
  const predictExtractedValue = (fieldName: string, labelText: string, lineOffset: number): string => {
    if (!pdfText || !labelText) return '';
    
    const lines = pdfText.split('\n');
    
    // Find label in text (simple case-sensitive search)
    const labelIndex = pdfText.indexOf(labelText);
    if (labelIndex === -1) return '';
    
    // Calculate line number where label appears
    const labelLineNum = pdfText.substring(0, labelIndex).split('\n').length - 1;
    const targetLineNum = labelLineNum + lineOffset;
    
    if (targetLineNum < 0 || targetLineNum >= lines.length) return '';
    
    let targetLine = lines[targetLineNum].trim();
    if (!targetLine) return '';
    
    // If offset is 0, remove label from extracted value
    if (lineOffset === 0) {
      const labelInLine = targetLine.indexOf(labelText);
      if (labelInLine >= 0) {
        const afterLabel = targetLine.substring(labelInLine + labelText.length).trim();
        targetLine = afterLabel.replace(/^[:;\-\s]+/, '').trim();
      }
    }
    
    // Apply field-specific processing
    if (fieldName === 'amount' && targetLine) {
      const amountMatch = targetLine.match(/\d+[,\.]?\d*/);
      if (amountMatch) {
        const amountStr = amountMatch[0].trim();
        const cleaned = amountStr.replace(/[,\.\s]/g, '');
        try {
          const amountBani = parseInt(cleaned);
          return (amountBani / 100.0).toString();
        } catch {
          return amountStr;
        }
      }
      return targetLine;
    } else if (fieldName === 'currency') {
      const currencyMatch = targetLine.match(/[A-Z]{3}/i);
      if (currencyMatch) {
        const currency = currencyMatch[0].toUpperCase();
        return currency === 'LEI' ? 'RON' : currency;
      }
      return 'RON';
    } else if (fieldName === 'iban' && targetLine) {
      // Remove spaces and extract IBAN (international format)
      // IBAN format: [Country Code (2 letters)][Check Digits (2 digits)][BBAN (varies by country)]
      const cleaned = targetLine.replace(/\s+/g, '').toUpperCase();
      
      // IBAN lengths by country code (most common ones)
      const ibanLengths: { [key: string]: number } = {
        'RO': 24, 'DE': 22, 'GB': 22, 'FR': 27, 'IT': 27, 'ES': 24, 'NL': 18,
        'BE': 16, 'AT': 20, 'PL': 28, 'CH': 21, 'SE': 24, 'NO': 15, 'DK': 18,
        'FI': 18, 'PT': 25, 'GR': 27, 'CZ': 24, 'HU': 28, 'IE': 22, 'SK': 24
      };
      
      // Find IBAN start: country code + check digits
      const startMatch = cleaned.match(/[A-Z]{2}\d{2}/);
      if (startMatch) {
        const startPos = startMatch.index!;
        const countryCode = cleaned.substring(startPos, startPos + 2);
        const expectedLength = ibanLengths[countryCode];
        
        if (expectedLength && startPos + expectedLength <= cleaned.length) {
          const iban = cleaned.substring(startPos, startPos + expectedLength);
          // Verify it's all alphanumeric
          if (/^[A-Z0-9]+$/.test(iban)) {
            return iban;
          }
        }
        
        // Fallback: try common lengths and check for bank name words after
        const bankWords = ['BANCA', 'BANK', 'BANQUE', 'BANCO', 'BANKI', 'BANKA'];
        for (const length of [15, 16, 18, 20, 22, 24, 27, 28, 34]) {
          if (startPos + length <= cleaned.length) {
            const candidate = cleaned.substring(startPos, startPos + length);
            if (/^[A-Z0-9]+$/.test(candidate)) {
              // Check if next chars are start of bank word
              if (startPos + length < cleaned.length) {
                const nextChars = cleaned.substring(startPos + length, startPos + length + 5);
                if (!bankWords.some(w => nextChars.startsWith(w))) {
                  return candidate;
                }
              } else {
                return candidate;
              }
            }
          }
        }
      }
      
      // Final fallback: match pattern
      const ibanMatch = cleaned.match(/[A-Z]{2}\d{2}[A-Z0-9]{11,30}/);
      if (ibanMatch) {
        const iban = ibanMatch[0];
        if (iban.length >= 15 && iban.length <= 34) {
          return iban;
        }
      }
      
      return cleaned;
    } else if (fieldName === 'bill_number' && targetLine) {
      // Smart prefix removal - only remove if followed by alphanumeric
      const patterns = [
        /^Seria\s+ENG\s+nr\.?\s+/i,
        /^Seria\s+[A-Z]+\s+nr\.?\s+/i,
        /^nr\.?\s+/i,
        /^No\.\s+/i,
        /^NO\s+/,
        /^No\s+/i,
      ];
      
      for (const pattern of patterns) {
        const match = targetLine.match(pattern);
        if (match) {
          const remaining = targetLine.substring(match[0].length).trim();
          if (remaining && /^[A-Z0-9]/i.test(remaining)) {
            return remaining;
          }
        }
      }
      return targetLine.trim();
    } else if ((fieldName === 'due_date' || fieldName === 'bill_date') && targetLine) {
      // Try to parse date with month names
      const roMonths: { [key: string]: number } = {
        'ianuarie': 1, 'februarie': 2, 'martie': 3, 'aprilie': 4, 'mai': 5, 'iunie': 6,
        'iulie': 7, 'august': 8, 'septembrie': 9, 'octombrie': 10, 'noiembrie': 11, 'decembrie': 12
      };
      const enMonths: { [key: string]: number } = {
        'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
        'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12
      };
      
      const datePattern = /(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})/i;
      const match = targetLine.match(datePattern);
      
      if (match) {
        const day = parseInt(match[1]);
        const monthName = match[2].toLowerCase();
        const year = parseInt(match[3]);
        
        let month: number | undefined;
        if (monthName in roMonths) {
          month = roMonths[monthName];
        } else if (monthName in enMonths) {
          month = enMonths[monthName];
        }
        
        if (month) {
          return `${day.toString().padStart(2, '0')}/${month.toString().padStart(2, '0')}/${year}`;
        }
      }
      
      // Fallback to numeric date pattern
      const numericMatch = targetLine.match(/(\d{1,2})[\.\/\-](\d{1,2})[\.\/\-](\d{2,4})/);
      if (numericMatch) {
        const day = parseInt(numericMatch[1]);
        const month = parseInt(numericMatch[2]);
        let year = parseInt(numericMatch[3]);
        if (year < 100) {
          year += year < 50 ? 2000 : 1900;
        }
        return `${day.toString().padStart(2, '0')}/${month.toString().padStart(2, '0')}/${year}`;
      }
      
      return targetLine;
    }
    
    return targetLine;
  };
  
  const adjustLineOffset = (field: string, delta: number) => {
    const currentOffset = lineOffsets.get(field) || 0;
    const newOffset = Math.max(0, currentOffset + delta);
    
    setLineOffsets(prev => {
      const newMap = new Map(prev);
      newMap.set(field, newOffset);
      return newMap;
    });
    
    // Update pattern if it exists
    const existingPattern = fieldPatterns.get(field);
    if (existingPattern) {
      setFieldPatterns(prev => {
        const newMap = new Map(prev);
        newMap.set(field, { ...existingPattern, line_offset: newOffset });
        return newMap;
      });
    }
    
    // Highlight target line if label is selected and offset > 0
    if (selectedLabelStart !== null && newOffset > 0) {
      highlightTargetLine(selectedLabelStart, newOffset);
    } else if (newOffset === 0) {
      setHighlightedLine(null);
    }
  };

  const handleSavePattern = async () => {
    if (!token || !patternName || fieldPatterns.size === 0) {
      setError('Pattern name and at least one field pattern required');
      return;
    }
    
    setLoading(true);
    setError('');
    
    try {
      const pattern = {
        name: patternName,
        bill_type: billType,
        supplier: supplier || undefined,
        field_patterns: Array.from(fieldPatterns.values()).map(fp => ({
          field_name: fp.field_name,
          label_text: fp.label_text,
          line_offset: fp.line_offset,
        })),
      };
      
      const response = await fetch(`${API_URL}/text-patterns/save-pattern`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(pattern),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to save pattern');
      }
      
      setSuccess('Pattern saved successfully');
      setTimeout(() => setSuccess(''), 3000);
      // Reset form
      setPatternName('');
      setSupplier('');
      setFieldPatterns(new Map());
      setLineOffsets(new Map());
      setSelectedLabel('');
    } catch (err: any) {
      setError(err.message || 'Error saving pattern');
    } finally {
      setLoading(false);
    }
  };

  const handleMatchPdf = async (file: File) => {
    if (!token) return;
    setLoading(true);
    setMatchingPatterns(true);
    setError('');
    setMatches([]);
    setExtractionResult(null);
    setSelectedPatternId('');
    
    // First upload PDF to get text
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      // Upload PDF first
      const uploadResponse = await fetch(`${API_URL}/text-patterns/upload-pdf`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: formData,
      });
      
      if (!uploadResponse.ok) {
        const errorData = await uploadResponse.json();
        throw new Error(errorData.detail || 'Failed to upload PDF');
      }
      
      const uploadData = await uploadResponse.json();
      setPdfText(uploadData.text || '');
      
      // Reset formData for matching (need to recreate it)
      const matchFormData = new FormData();
      matchFormData.append('file', file);
      
      // Then match patterns
      const matchResponse = await fetch(`${API_URL}/text-patterns/match-pdf`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: matchFormData,
      });
      
      if (!matchResponse.ok) {
        const errorData = await matchResponse.json();
        throw new Error(errorData.detail || 'Failed to match PDF');
      }
      
      const matchData = await matchResponse.json();
      const allMatches = matchData.matches || [];
      console.log(`[Match PDF] Found ${allMatches.length} patterns:`, allMatches.map((m: any) => `${m.pattern_name} (${(m.confidence * 100).toFixed(1)}%)`));
      setMatches(allMatches);
      setMatchingPdf(file);
      // Auto-select best confidence pattern (first in sorted list)
      if (allMatches.length > 0) {
        const bestMatch = allMatches[0]; // Already sorted by confidence descending
        setSelectedPatternId(bestMatch.pattern_id);
        console.log(`[Match PDF] Auto-selecting best match: ${bestMatch.pattern_name} (${(bestMatch.confidence * 100).toFixed(1)}%)`);
        // Pass file directly to handleExtract to avoid state timing issues
        handleExtract(bestMatch.pattern_id, file);
      }
      // Clear file input so same file can be uploaded again
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    } catch (err: any) {
      setError(err.message || 'Error matching PDF');
    } finally {
      setLoading(false);
      setMatchingPatterns(false);
    }
  };

  const handleExtract = async (patternId: string, file?: File) => {
    const fileToUse = file || matchingPdf;
    if (!token || !fileToUse) return;
    setLoading(true);
    setError('');
    try {
      const formData = new FormData();
      formData.append('file', fileToUse);
      formData.append('pattern_id', patternId);
      
      const response = await fetch(`${API_URL}/text-patterns/extract-with-pattern`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: formData,
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Failed to extract data' }));
        throw new Error(errorData.detail || errorData.message || 'Failed to extract data');
      }
      
      const data = await response.json();
      setExtractionResult(data.extracted_data);
      setError(''); // Clear any previous errors
    } catch (err: any) {
      const errorMessage = err.message || 'Error extracting data';
      setError(errorMessage);
      console.error('Extraction error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleEditPdfUpload = async (file: File) => {
    if (!token) return;
    setLoading(true);
    setMatchingPatterns(true);
    setError('');
    setEditPdfFile(file);
    setEditMatches([]);
    setEditingPattern(null);
    setSelectedPatternId('');
    try {
      // Upload PDF to get text
      const formData = new FormData();
      formData.append('file', file);
      const uploadResponse = await fetch(`${API_URL}/text-patterns/upload-pdf`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: formData,
      });
      
      if (!uploadResponse.ok) {
        const errorData = await uploadResponse.json();
        throw new Error(errorData.detail || 'Failed to upload PDF');
      }
      
      const uploadData = await uploadResponse.json();
      setPdfText(uploadData.text || '');
      
      // Match patterns to get confidence scores
      const matchResponse = await fetch(`${API_URL}/text-patterns/match-pdf`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: formData,
      });
      
      if (!matchResponse.ok) {
        const errorData = await matchResponse.json();
        throw new Error(errorData.detail || 'Failed to match patterns');
      }
      
      const matchData = await matchResponse.json();
      const allEditMatches = matchData.matches || [];
      setEditMatches(allEditMatches);
      console.log(`[Edit PDF] Found ${allEditMatches.length} patterns:`, allEditMatches.map((m: any) => `${m.pattern_name} (${(m.confidence * 100).toFixed(1)}%)`));
      // Auto-select best confidence pattern (first in sorted list)
      if (allEditMatches.length > 0) {
        const bestMatch = allEditMatches[0]; // Already sorted by confidence descending
        setSelectedPatternId(bestMatch.pattern_id);
        console.log(`[Edit PDF] Auto-selecting best match: ${bestMatch.pattern_name} (${(bestMatch.confidence * 100).toFixed(1)}%)`);
        loadPatternForEditing(bestMatch.pattern_id);
      }
      // Clear file input so same file can be uploaded again
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      setError('');
    } catch (err: any) {
      setError(err.message || 'Error processing PDF');
    } finally {
      setLoading(false);
      setMatchingPatterns(false);
    }
  };

  const loadPatternForEditing = async (patternId: string) => {
    if (!token) return;
    setLoading(true);
    setError('');
    try {
      const response = await fetch(`${API_URL}/text-patterns/get-pattern/${patternId}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      if (!response.ok) throw new Error('Failed to load pattern');
      const pattern = await response.json();
      
      setEditingPattern(pattern);
      setPatternName(pattern.name || '');
      setSupplier(pattern.supplier || '');
      setBillType(pattern.bill_type || 'utilities');
      
      // Load existing field patterns
      const existingPatterns = new Map<string, FieldPattern>();
      const existingOffsets = new Map<string, number>();
      if (pattern.field_patterns) {
        for (const fp of pattern.field_patterns) {
          existingPatterns.set(fp.field_name, {
            field_name: fp.field_name,
            label_text: fp.label_text,
            line_offset: fp.line_offset,
          });
          existingOffsets.set(fp.field_name, fp.line_offset);
        }
      }
      setFieldPatterns(existingPatterns);
      setLineOffsets(existingOffsets);
      
      // Keep PDF text - user already uploaded it
    } catch (err: any) {
      setError(err.message || 'Error loading pattern');
    } finally {
      setLoading(false);
    }
  };

  const renderPatternEditor = (mode: 'create' | 'edit') => {
    return (
      <div className="space-y-4">
        {mode === 'edit' && editingPattern && (
          <div className="flex justify-between items-center">
            <div className="text-sm text-slate-400">
              Editing: <span className="text-slate-300 font-semibold">{editingPattern.name}</span>
              <br />
              Existing fields will be preserved. Add new fields below.
            </div>
            <Button
              onClick={() => {
                setEditingPattern(null);
                setSelectedPatternId('');
                // Keep PDF text and matches - don't clear them
              }}
              variant="outline"
              className="bg-slate-700 border-slate-600 text-slate-100"
            >
              Cancel
            </Button>
          </div>
        )}
        
        <div className="flex gap-4 items-center">
          <div className="flex gap-2 items-center">
            <Label className="text-slate-300">Field</Label>
            <Select value={currentField} onValueChange={(value) => {
              setCurrentField(value);
              setSelectedLabel('');
              setSelectedLabelStart(null);
              setHighlightedLine(null);
            }}>
              <SelectTrigger className="w-48 bg-slate-700 border-slate-600 text-slate-100">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-slate-700 border-slate-600">
                {fieldOptions.map(opt => (
                  <SelectItem key={opt.value} value={opt.value} className="text-slate-100">
                    {opt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          
          <div className="flex gap-2 items-center">
            <Label className="text-slate-300">Line Offset:</Label>
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={() => adjustLineOffset(currentField, -1)}
              className="h-8 w-8 bg-slate-700 border-slate-600 text-slate-100"
            >
              -
            </Button>
            <span className="w-8 text-center text-slate-300">
              {lineOffsets.get(currentField) || 0}
            </span>
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={() => adjustLineOffset(currentField, 1)}
              className="h-8 w-8 bg-slate-700 border-slate-600 text-slate-100"
            >
              +
            </Button>
          </div>
          
          {fieldPatterns.get(currentField) && (
            <div className="flex gap-2 items-center text-sm text-slate-400">
              <span>
                Label: "{fieldPatterns.get(currentField)!.label_text}" 
                (offset: {fieldPatterns.get(currentField)!.line_offset})
              </span>
              <span className="text-slate-500">|</span>
              <span className="text-slate-300">
                Value: "{predictExtractedValue(
                  currentField,
                  fieldPatterns.get(currentField)!.label_text,
                  fieldPatterns.get(currentField)!.line_offset
                )}"
              </span>
            </div>
          )}
        </div>
        
        <div className="space-y-2">
          <textarea
            ref={textAreaRef}
            value={pdfText}
            readOnly
            onMouseUp={handleTextSelection}
            onKeyUp={handleTextSelection}
            className="w-full h-96 p-4 bg-white text-black font-mono text-sm rounded border border-slate-600"
            style={{ 
              whiteSpace: 'pre-wrap', 
              wordWrap: 'break-word'
            }}
          />
          {highlightedLine !== null && (
            <div className="text-xs text-slate-400 mt-1">
              Highlighted line {highlightedLine + 1} (target line for extraction)
            </div>
          )}
          <div className="text-sm text-slate-400">
            Instructions: Select the label text in the PDF. Use +/- buttons to adjust line offset (default: 0). 
            If offset is 0, the value will be automatically extracted from the same line after the label.
          </div>
        </div>
        
        <div className="space-y-4">
          <div>
            <Label className="text-slate-300">Pattern Name</Label>
            <Input
              value={patternName}
              onChange={(e) => setPatternName(e.target.value)}
              className="bg-slate-700 border-slate-600 text-slate-100"
              placeholder="e.g., Engie Gas Bill"
            />
          </div>
          
          <div>
            <Label className="text-slate-300">Supplier</Label>
            <Input
              value={supplier}
              onChange={(e) => setSupplier(e.target.value)}
              className="bg-slate-700 border-slate-600 text-slate-100"
              placeholder="Supplier name (used as legal_name if payment not selected)"
            />
          </div>
          
          <div>
            <Label className="text-slate-300">Bill Type</Label>
            <Select value={billType} onValueChange={(v: any) => setBillType(v)}>
              <SelectTrigger className="bg-slate-700 border-slate-600 text-slate-100">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-slate-700 border-slate-600">
                <SelectItem value="utilities" className="text-slate-100">Utilities</SelectItem>
                <SelectItem value="rent" className="text-slate-100">Rent</SelectItem>
                <SelectItem value="ebloc" className="text-slate-100">E-Bloc</SelectItem>
                <SelectItem value="other" className="text-slate-100">Other</SelectItem>
              </SelectContent>
            </Select>
          </div>
          
          <Button
            onClick={mode === 'create' ? handleSavePattern : handleUpdatePattern}
            disabled={loading || !patternName || fieldPatterns.size === 0}
            className="bg-emerald-600 hover:bg-emerald-700"
          >
            <Save className="w-4 h-4 mr-2" />
            {mode === 'create' ? 'Save Pattern' : 'Update Pattern'}
          </Button>
        </div>
      </div>
    );
  };

  const handleUpdatePattern = async () => {
    if (!token || !editingPattern || !patternName || fieldPatterns.size === 0) {
      setError('Pattern name and at least one field pattern required');
      return;
    }
    
    setLoading(true);
    setError('');
    try {
      const response = await fetch(`${API_URL}/text-patterns/update-pattern/${editingPattern.id}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: patternName,
          bill_type: billType,
          supplier: supplier,
          field_patterns: Array.from(fieldPatterns.values()).map(fp => ({
            field_name: fp.field_name,
            label_text: fp.label_text,
            line_offset: fp.line_offset,
          })),
        }),
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Failed to update pattern' }));
        throw new Error(errorData.detail || errorData.message || 'Failed to update pattern');
      }
      
      setSuccess('Pattern updated successfully');
      setTimeout(() => setSuccess(''), 3000);
      
      // Reload pattern matches if PDF is still loaded
      if (editPdfFile) {
        await handleEditPdfUpload(editPdfFile);
      }
    } catch (err: any) {
      setError(err.message || 'Error updating pattern');
    } finally {
      setLoading(false);
    }
  };


  return (
    <Card className="bg-slate-800 border-slate-700">
      <CardHeader>
        <CardTitle className="text-slate-100">Tools</CardTitle>
        <CardDescription className="text-slate-400">
          Create text-based extraction patterns by selecting labels and values from PDF text
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="create" value={activeTab} onValueChange={(value) => {
          setActiveTab(value);
          // Clear file input so same file can be uploaded again
          if (fileInputRef.current) {
            fileInputRef.current.value = '';
          }
          // Clear form when switching to create tab
          if (value === 'create') {
            setPdfText('');
            setFieldPatterns(new Map());
            setLineOffsets(new Map());
            setPatternName('');
            setSupplier('');
            setBillType('utilities');
            setSelectedLabel('');
            setSelectedLabelStart(null);
            setHighlightedLine(null);
            setCurrentField('amount');
          }
          // Clear extraction result when switching to match tab
          if (value === 'match') {
            setExtractionResult(null);
            setSelectedPatternId('');
            setMatches([]);
            setMatchingPdf(null);
            setPdfText('');
          }
          // Clear edit state when switching to edit tab
          if (value === 'edit') {
            setEditingPattern(null);
            setSelectedPatternId('');
            setEditMatches([]);
            setEditPdfFile(null);
            setPdfText('');
            setFieldPatterns(new Map());
            setLineOffsets(new Map());
            setPatternName('');
            setSupplier('');
            setBillType('utilities');
          }
        }} className="space-y-4">
          <div className="flex items-center gap-4 flex-wrap">
            <TabsList className="bg-slate-700 border border-slate-600">
              <TabsTrigger value="create" className="data-[state=active]:bg-slate-600">Create Pattern</TabsTrigger>
              <TabsTrigger value="match" className="data-[state=active]:bg-slate-600">Match Pattern</TabsTrigger>
              {user?.role === 'admin' && (
                <TabsTrigger value="edit" className="data-[state=active]:bg-slate-600">Edit Pattern</TabsTrigger>
              )}
            </TabsList>
            
            <div className="flex items-center gap-2">
              <label htmlFor="pdf-upload" className="cursor-pointer">
              <input
                ref={fileInputRef}
                id="pdf-upload"
                type="file"
                accept=".pdf"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) {
                    if (activeTab === 'create') {
                      handleFileUpload(file);
                    } else if (activeTab === 'edit') {
                      handleEditPdfUpload(file);
                    } else {
                      handleMatchPdf(file);
                    }
                    // Clear input value so same file can be uploaded again
                    e.target.value = '';
                  }
                }}
                disabled={loading}
                className="hidden"
              />
                <Button
                  type="button"
                  variant="outline"
                  disabled={loading}
                  className="flex items-center gap-2 border-slate-600 bg-green-600/20 hover:bg-green-600/30 text-green-400 disabled:opacity-50 disabled:cursor-not-allowed"
                  onClick={() => document.getElementById('pdf-upload')?.click()}
                >
                  <Upload className="h-4 w-4" />
                  Upload PDF
                </Button>
              </label>
              
              {activeTab === 'match' && matchingPdf && (
                matchingPatterns ? (
                  <div className="text-slate-400 text-sm flex items-center gap-2">
                    <div className="animate-spin h-4 w-4 border-2 border-slate-400 border-t-transparent rounded-full"></div>
                    Calculating confidence...
                  </div>
                ) : matches.length > 0 ? (
                  <Select 
                    value={selectedPatternId} 
                    onValueChange={(value) => {
                      setSelectedPatternId(value);
                      if (value && matchingPdf) {
                        handleExtract(value, matchingPdf);
                      }
                    }}
                    disabled={loading}
                  >
                    <SelectTrigger className="w-80 bg-slate-700 border-slate-600 text-slate-100">
                      <SelectValue placeholder="Select pattern to extract..." />
                    </SelectTrigger>
                    <SelectContent className="bg-slate-700 border-slate-600">
                      {matches.map((match) => (
                        <SelectItem key={match.pattern_id} value={match.pattern_id} className="text-slate-100">
                          {match.pattern_name} ({(match.confidence * 100).toFixed(1)}% - {match.matched_fields}/{match.total_fields} fields)
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                ) : null
              )}
              
              {activeTab === 'edit' && pdfText && (
                matchingPatterns ? (
                  <div className="text-slate-400 text-sm flex items-center gap-2">
                    <div className="animate-spin h-4 w-4 border-2 border-slate-400 border-t-transparent rounded-full"></div>
                    Calculating confidence...
                  </div>
                ) : editMatches.length > 0 ? (
                  <Select 
                    value={selectedPatternId} 
                    onValueChange={(value) => {
                      setSelectedPatternId(value);
                      if (value) {
                        loadPatternForEditing(value);
                      }
                    }}
                    disabled={loading}
                  >
                    <SelectTrigger className="w-80 bg-slate-700 border-slate-600 text-slate-100">
                      <SelectValue placeholder="Select pattern to edit..." />
                    </SelectTrigger>
                    <SelectContent className="bg-slate-700 border-slate-600">
                      {editMatches.map((match) => (
                        <SelectItem key={match.pattern_id} value={match.pattern_id} className="text-slate-100">
                          {match.pattern_name} ({(match.confidence * 100).toFixed(1)}% - {match.matched_fields}/{match.total_fields} fields)
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                ) : null
              )}
            </div>
          </div>
          
          <TabsContent value="create" className="space-y-4">
            <div className="space-y-4">
              {pdfText && renderPatternEditor('create')}
            </div>
          </TabsContent>
          
          <TabsContent value="match" className="space-y-4">
            <div className="space-y-4">
              {!pdfText && (
                <div className="text-slate-400 text-center py-8">
                  Upload a PDF to match against patterns
                </div>
              )}
              
              {pdfText && matches.length === 0 && !loading && (
                <div className="text-slate-400 text-center py-8">
                  No matching patterns found
                </div>
              )}
              
              {extractionResult && (
                <div className="space-y-2">
                  <Label className="text-slate-300">Extracted Data</Label>
                  <pre className="p-4 bg-slate-900 text-slate-100 rounded border border-slate-600 overflow-auto">
                    {JSON.stringify(extractionResult, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          </TabsContent>
          
          {user?.role === 'admin' && (
            <TabsContent value="edit" className="space-y-4">
              <div className="space-y-4">
                {!pdfText && (
                  <div className="text-slate-400 text-center py-8">
                    Upload a PDF to see matching patterns sorted by confidence level
                  </div>
                )}
                
                {pdfText && editMatches.length === 0 && !loading && (
                  <div className="text-slate-400 text-center py-8">
                    No matching patterns found. Upload a PDF to match against existing patterns.
                  </div>
                )}
                
                {editingPattern && pdfText && renderPatternEditor('edit')}
              </div>
            </TabsContent>
          )}
        </Tabs>
        
        {error && (
          <Alert className="mt-4 bg-red-900/50 border-red-700">
            <AlertDescription className="text-red-200">{error}</AlertDescription>
          </Alert>
        )}
        
        {success && (
          <Alert className="mt-4 bg-emerald-900/50 border-emerald-700">
            <AlertDescription className="text-emerald-200">{success}</AlertDescription>
          </Alert>
        )}
      </CardContent>
      
    </Card>
  );
}


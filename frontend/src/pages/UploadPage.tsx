import { useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { useMutation } from '@tanstack/react-query';
import { uploadDataset } from '../api/datasets';
import { startScoring } from '../api/scoring';
import { useNavigate } from 'react-router-dom';
import { Upload, FileText, CheckCircle, AlertTriangle, Loader } from 'lucide-react';
import type { UploadResponse } from '../types';

export default function UploadPage() {
  const navigate = useNavigate();
  const [uploadResult, setUploadResult] = useState<UploadResponse | null>(null);

  const uploadMutation = useMutation({
    mutationFn: uploadDataset,
    onSuccess: (data) => setUploadResult(data),
  });

  const scoringMutation = useMutation({
    mutationFn: (datasetId: string) => startScoring(datasetId),
    onSuccess: (data) => {
      navigate(`/datasets/${uploadResult?.dataset_id}`);
    },
  });

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: { 'application/jsonl': ['.jsonl'] },
    maxFiles: 1,
    onDrop: (files) => {
      if (files.length > 0) {
        setUploadResult(null);
        uploadMutation.mutate(files[0]);
      }
    },
  });

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <h2 className="text-2xl font-bold">Upload Dataset</h2>

      {/* Dropzone */}
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-colors ${
          isDragActive ? 'border-orange-500 bg-orange-500/5' : 'border-gray-700 hover:border-gray-600'
        }`}
      >
        <input {...getInputProps()} />
        {uploadMutation.isPending ? (
          <div className="flex flex-col items-center gap-3">
            <Loader className="w-10 h-10 text-orange-500 animate-spin" />
            <p className="text-gray-400">Uploading and parsing...</p>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-3">
            <Upload className="w-10 h-10 text-gray-500" />
            <p className="text-gray-300">Drag & drop a .jsonl file here</p>
            <p className="text-gray-600 text-sm">or click to browse</p>
          </div>
        )}
      </div>

      {/* Upload result */}
      {uploadResult && (
        <div className="bg-gray-900 rounded-xl p-6 border border-gray-800 space-y-4">
          <div className="flex items-center gap-2 text-green-400">
            <CheckCircle className="w-5 h-5" />
            <h3 className="font-semibold">Upload Complete</h3>
          </div>

          <div className="grid grid-cols-3 gap-4 text-sm">
            <div>
              <p className="text-gray-500">File</p>
              <p className="font-medium flex items-center gap-1"><FileText className="w-4 h-4" />{uploadResult.filename}</p>
            </div>
            <div>
              <p className="text-gray-500">Valid Lines</p>
              <p className="font-medium text-green-400">{uploadResult.valid_lines.toLocaleString()}</p>
            </div>
            <div>
              <p className="text-gray-500">Invalid Lines</p>
              <p className={`font-medium ${uploadResult.invalid_lines > 0 ? 'text-yellow-400' : 'text-gray-400'}`}>
                {uploadResult.invalid_lines}
              </p>
            </div>
          </div>

          {uploadResult.errors.length > 0 && (
            <div className="bg-yellow-500/10 rounded-lg p-3 text-sm">
              <div className="flex items-center gap-1 text-yellow-400 mb-2">
                <AlertTriangle className="w-4 h-4" />
                <span className="font-medium">Validation Errors</span>
              </div>
              <ul className="text-yellow-300/80 space-y-1">
                {uploadResult.errors.slice(0, 5).map((err, i) => (
                  <li key={i} className="font-mono text-xs">{err}</li>
                ))}
                {uploadResult.errors.length > 5 && (
                  <li className="text-yellow-500">...and {uploadResult.errors.length - 5} more</li>
                )}
              </ul>
            </div>
          )}

          <button
            onClick={() => scoringMutation.mutate(uploadResult.dataset_id)}
            disabled={scoringMutation.isPending}
            className="w-full bg-orange-500 hover:bg-orange-600 disabled:bg-orange-500/50 text-white font-medium py-3 rounded-lg transition-colors"
          >
            {scoringMutation.isPending ? 'Starting Scoring...' : 'Start Quality Scoring'}
          </button>
        </div>
      )}

      {uploadMutation.isError && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-400 text-sm">
          Upload failed: {(uploadMutation.error as Error).message}
        </div>
      )}
    </div>
  );
}

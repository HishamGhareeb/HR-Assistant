import { useState } from "react";
import { api, ApiError } from "../api/client";
import type {
  BahrainContributionBranch,
  BahrainContributionPayer,
  BahrainWorkerCategory,
  CitationOut,
  EosbGratuityResponse,
  EosbMonthlyContributionResponse,
  SioContributionResponse,
  WpsValidationResponse,
} from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { StateView } from "../components/StateView";
import { StatusChip } from "../components/StatusChip";

const TODAY = new Date().toISOString().slice(0, 10);

const WORKER_CATEGORIES: BahrainWorkerCategory[] = [
  "bahraini_private_sector",
  "non_bahraini_private_sector",
  "gcc_national",
  "domestic_worker",
  "public_sector",
  "self_employed",
  "flexi_or_successor",
];

const CONTRIBUTION_BRANCHES: BahrainContributionBranch[] = [
  "pension",
  "employment_injury",
  "unemployment",
  "end_of_service_benefit",
];

const PAYERS: BahrainContributionPayer[] = ["employee", "employer", "labour_fund", "government"];

export function PayrollPage() {
  const { session } = useAuth();
  const [notice, setNotice] = useState<string | null>(null);
  const [sioResult, setSioResult] = useState<SioContributionResponse | null>(null);
  const [eosbMonthlyResult, setEosbMonthlyResult] = useState<EosbMonthlyContributionResponse | null>(null);
  const [eosbGratuityResult, setEosbGratuityResult] = useState<EosbGratuityResponse | null>(null);
  const [wpsResult, setWpsResult] = useState<WpsValidationResponse | null>(null);

  async function run<T>(operation: () => Promise<T>, onSuccess: (result: T) => void) {
    if (!session) return;
    setNotice(null);
    try {
      onSuccess(await operation());
    } catch (err) {
      setNotice(err instanceof ApiError ? err.detail : "Could not reach the payroll API.");
    }
  }

  return (
    <>
      <div className="page-header">
        <h1>Bahrain Payroll</h1>
        <p>
          Source-backed Bahrain payroll checks for HR admins. The frontend only submits scenarios; all calculations and
          citations come from the RAL backend rule pack.
        </p>
      </div>

      {notice && (
        <div className="state-banner state-banner--error" style={{ marginBottom: 16 }}>
          {notice}
        </div>
      )}

      <div className="grid two-col">
        <SioContributionCard
          onSubmit={(payload) =>
            run(() => api.calculateSioContribution(session!.token, payload), (result) => setSioResult(result))
          }
          result={sioResult}
        />
        <EosbMonthlyCard
          onSubmit={(payload) =>
            run(() => api.calculateEosbMonthlyContribution(session!.token, payload), (result) =>
              setEosbMonthlyResult(result),
            )
          }
          result={eosbMonthlyResult}
        />
      </div>

      <div className="grid two-col" style={{ marginTop: 16 }}>
        <EosbGratuityCard
          onSubmit={(payload) =>
            run(() => api.calculateEosbGratuity(session!.token, payload), (result) => setEosbGratuityResult(result))
          }
          result={eosbGratuityResult}
        />
        <WpsValidationCard
          onSubmit={(payload) =>
            run(() => api.validateWpsSalaryFile(session!.token, payload), (result) => setWpsResult(result))
          }
          result={wpsResult}
        />
      </div>
    </>
  );
}

function SioContributionCard({
  onSubmit,
  result,
}: {
  onSubmit: (payload: Parameters<typeof api.calculateSioContribution>[1]) => void;
  result: SioContributionResponse | null;
}) {
  const [workerCategory, setWorkerCategory] = useState<BahrainWorkerCategory>("bahraini_private_sector");
  const [branch, setBranch] = useState<BahrainContributionBranch>("pension");
  const [payer, setPayer] = useState<BahrainContributionPayer>("employee");
  const [monthlyWage, setMonthlyWage] = useState("1000");
  const [asOf, setAsOf] = useState(TODAY);

  return (
    <section className="card">
      <h2>SIO contribution</h2>
      <p className="muted">Checks whether the selected contribution rate is source-backed, then calculates the amount.</p>
      <div className="inline-form">
        <Select label="Worker category" value={workerCategory} options={WORKER_CATEGORIES} onChange={setWorkerCategory} />
        <Select label="Branch" value={branch} options={CONTRIBUTION_BRANCHES} onChange={setBranch} />
        <Select label="Payer" value={payer} options={PAYERS} onChange={setPayer} />
      </div>
      <MoneyDateInputs amount={monthlyWage} setAmount={setMonthlyWage} date={asOf} setDate={setAsOf} />
      <button
        className="btn btn-primary btn-sm"
        onClick={() =>
          onSubmit({
            worker_category: workerCategory,
            branch,
            payer,
            monthly_wage: monthlyWage,
            as_of: asOf,
          })
        }
      >
        Calculate contribution
      </button>
      {result && <SupportedResult result={result} />}
    </section>
  );
}

function EosbMonthlyCard({
  onSubmit,
  result,
}: {
  onSubmit: (payload: Parameters<typeof api.calculateEosbMonthlyContribution>[1]) => void;
  result: EosbMonthlyContributionResponse | null;
}) {
  const [hireDate, setHireDate] = useState("2022-01-01");
  const [monthlyWage, setMonthlyWage] = useState("1000");
  const [asOf, setAsOf] = useState(TODAY);

  return (
    <section className="card">
      <h2>EOSB monthly contribution</h2>
      <p className="muted">Transition-aware monthly funded EOSB contribution for non-Bahraini private-sector workers.</p>
      <div className="inline-form">
        <DateField label="Hire date" value={hireDate} onChange={setHireDate} />
        <DateField label="As of" value={asOf} onChange={setAsOf} />
        <MoneyField label="Monthly wage (BHD)" value={monthlyWage} onChange={setMonthlyWage} />
      </div>
      <button
        className="btn btn-primary btn-sm"
        onClick={() => onSubmit({ hire_date: hireDate, monthly_wage: monthlyWage, as_of: asOf })}
      >
        Calculate monthly EOSB
      </button>
      {result?.unsupported && <UnsupportedBox reason={result.unsupported.message} />}
      {result?.result && (
        <ResultTable
          rows={[
            ["Rate", `${result.result.contribution_rate_percent}%`],
            ["Employer monthly contribution", `BHD ${result.result.employer_monthly_contribution_amount}`],
            ["Total completed service years", result.result.total_completed_service_years],
            ["Pre-March 2024 years", result.result.pre_march_2024_completed_service_years],
          ]}
        />
      )}
      {result?.result && <CitationList citations={result.result.figures.map((figure) => figure.citation)} />}
    </section>
  );
}

function EosbGratuityCard({
  onSubmit,
  result,
}: {
  onSubmit: (payload: Parameters<typeof api.calculateEosbGratuity>[1]) => void;
  result: EosbGratuityResponse | null;
}) {
  const [basicSalary, setBasicSalary] = useState("900");
  const [socialAllowance, setSocialAllowance] = useState("100");
  const [hireDate, setHireDate] = useState("2020-01-01");
  const [terminationDate, setTerminationDate] = useState(TODAY);

  return (
    <section className="card">
      <h2>EOSB gratuity split</h2>
      <p className="muted">Separates pre-2024 employer liability from post-2024 funded EOSB amounts.</p>
      <div className="inline-form">
        <MoneyField label="Basic salary" value={basicSalary} onChange={setBasicSalary} />
        <MoneyField label="Social allowance" value={socialAllowance} onChange={setSocialAllowance} />
      </div>
      <div className="inline-form">
        <DateField label="Hire date" value={hireDate} onChange={setHireDate} />
        <DateField label="Termination date" value={terminationDate} onChange={setTerminationDate} />
      </div>
      <button
        className="btn btn-primary btn-sm"
        onClick={() =>
          onSubmit({
            monthly_basic_salary: basicSalary,
            monthly_social_allowance: socialAllowance,
            hire_date: hireDate,
            termination_date: terminationDate,
          })
        }
      >
        Calculate gratuity
      </button>
      {result && (
        <>
          <ResultTable
            rows={[
              ["Pre-2024 direct liability", `BHD ${result.pre_march_2024_employer_direct_liability}`],
              ["Post-2024 funded amount", `BHD ${result.post_march_2024_sio_funded_amount}`],
              ["Total", `BHD ${result.total_amount}`],
            ]}
          />
          <CitationList citations={result.figures.map((figure) => figure.citation)} />
        </>
      )}
    </section>
  );
}

function WpsValidationCard({
  onSubmit,
  result,
}: {
  onSubmit: (payload: Parameters<typeof api.validateWpsSalaryFile>[1]) => void;
  result: WpsValidationResponse | null;
}) {
  const [payrollMonth, setPayrollMonth] = useState("2026-08");
  const [transferDate, setTransferDate] = useState(TODAY);

  return (
    <section className="card">
      <h2>WPS validation</h2>
      <p className="muted">Runs a sample salary-file validation against the backend WPS rule pack.</p>
      <div className="inline-form">
        <div className="field" style={{ margin: 0 }}>
          <label>Payroll month</label>
          <input value={payrollMonth} onChange={(event) => setPayrollMonth(event.target.value)} />
        </div>
        <DateField label="Transfer date" value={transferDate} onChange={setTransferDate} />
      </div>
      <button
        className="btn btn-primary btn-sm"
        onClick={() =>
          onSubmit({
            payroll_month: payrollMonth,
            scheduled_transfer_date: transferDate,
            actual_transfer_date: transferDate,
            worker_payments: [
              {
                employee_full_name: "Priya Nair",
                employee_id_number: "900101123",
                wage_amount: "1000",
                payment_date: transferDate,
                employee_account_identifier: "BH67BMAG00001299123456",
                employer_account_number: "BH29BMAG1299123456",
                employer_id_cr_number: "196651-1",
                fixed_salary: "900",
                social_allowance: "100",
                variable_salary: "0",
                payment_status: "paid",
              },
            ],
            approvals: [
              { actor_user_id: "payroll-maker", role: "maker", action: "submitted", acted_at: transferDate },
              { actor_user_id: "payroll-checker", role: "checker", action: "approved", acted_at: transferDate },
              { actor_user_id: "payroll-wrp", role: "wrp", action: "approved", acted_at: transferDate },
            ],
            non_payment_justifications: [],
          })
        }
      >
        Validate sample WPS file
      </button>
      {result && (
        <>
          <div style={{ marginTop: 14 }}>
            <StatusChip tone={result.is_valid ? "success" : "failed"}>{result.is_valid ? "Valid" : "Needs review"}</StatusChip>
          </div>
          {result.errors.length > 0 ? (
            <ul>
              {result.errors.map((error) => (
                <li key={`${error.code}-${error.employee_id_number ?? "file"}`}>{error.message}</li>
              ))}
            </ul>
          ) : (
            <StateView kind="empty">No WPS validation errors returned.</StateView>
          )}
          <CitationList citations={result.citations} />
        </>
      )}
    </section>
  );
}

function SupportedResult({ result }: { result: SioContributionResponse }) {
  if (result.unsupported) return <UnsupportedBox reason={result.unsupported.message} />;
  if (!result.result) return null;
  return (
    <>
      <ResultTable
        rows={[
          ["Rate", `${result.result.rate_percent}%`],
          ["Amount", `BHD ${result.result.amount}`],
          ["Rate code", result.result.rate_code],
        ]}
      />
      <CitationList citations={[result.result.figure.citation]} />
    </>
  );
}

function UnsupportedBox({ reason }: { reason: string }) {
  return (
    <div className="state-banner state-banner--blocked" style={{ marginTop: 14 }}>
      <strong>Not calculated.</strong> {reason}
    </div>
  );
}

function ResultTable({ rows }: { rows: [string, string][] }) {
  return (
    <div className="table-wrap" style={{ marginTop: 14 }}>
      <table className="data-table">
        <tbody>
          {rows.map(([label, value]) => (
            <tr key={label}>
              <th>{label}</th>
              <td>{value}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function CitationList({ citations }: { citations: CitationOut[] }) {
  const unique = citations.filter(
    (citation, index, list) =>
      list.findIndex((other) => other.section === citation.section && other.instrument === citation.instrument) === index,
  );
  return (
    <details style={{ marginTop: 12 }}>
      <summary>Legal citations used</summary>
      <ul className="citation-list">
        {unique.map((citation) => (
          <li key={`${citation.section}-${citation.instrument}`}>
            <strong>{citation.section}</strong> — {citation.instrument}
          </li>
        ))}
      </ul>
    </details>
  );
}

function MoneyDateInputs({
  amount,
  setAmount,
  date,
  setDate,
}: {
  amount: string;
  setAmount: (value: string) => void;
  date: string;
  setDate: (value: string) => void;
}) {
  return (
    <div className="inline-form">
      <MoneyField label="Monthly wage (BHD)" value={amount} onChange={setAmount} />
      <DateField label="As of" value={date} onChange={setDate} />
    </div>
  );
}

function MoneyField({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <div className="field" style={{ margin: 0 }}>
      <label>{label}</label>
      <input type="number" min="0" step="0.001" value={value} onChange={(event) => onChange(event.target.value)} />
    </div>
  );
}

function DateField({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <div className="field" style={{ margin: 0 }}>
      <label>{label}</label>
      <input type="date" value={value} onChange={(event) => onChange(event.target.value)} />
    </div>
  );
}

function Select<T extends string>({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: T;
  options: T[];
  onChange: (value: T) => void;
}) {
  return (
    <div className="field" style={{ margin: 0 }}>
      <label>{label}</label>
      <select value={value} onChange={(event) => onChange(event.target.value as T)}>
        {options.map((option) => (
          <option key={option} value={option}>
            {option.replaceAll("_", " ")}
          </option>
        ))}
      </select>
    </div>
  );
}
